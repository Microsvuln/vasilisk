import logging
import os
import subprocess
import uuid

from datetime import datetime

from coverage.groups import recorder

from .base import BaseFuzzer


class GroupFuzzer(BaseFuzzer):
    def __init__(self, threads, d8, crashes, tests, debug, coverage_tests = True):
        self.logger = logging.getLogger(__name__)

        self.d8 = d8
        self.crashes = crashes
        self.tests = tests
        self.debug = debug
        self.coverage_tests = coverage_tests
        self.coverage_count = 0
        self.group_flag = True
        self.group_size = 20

        coverage_dir = os.path.join('/tmp', 'vasilisk_coverage')
        if not os.path.exists(coverage_dir):
            self.logger.info('creating coverage dir')
            os.makedirs(coverage_dir)

        self.coverage_paths = []
        for thread in range(threads):
            coverage_path = os.path.join(
                coverage_dir, 'thread-{}'.format(thread)
            )
            self.coverage_paths.append(coverage_path)

            if not os.path.exists(coverage_path):
                self.logger.info('creating thread specific coverage dir')
                os.makedirs(coverage_path)

        self.coverage = recorder.CoverageRecorder()

    def execute(self, test_case, thread):
        options = ['--allow-natives-syntax', '--trace-turbo',
                   '--trace-turbo-path', self.coverage_paths[thread], '-e']

        cmd = ' '.join([self.d8] + options + [test_case])
        if self.coverage_tests:
            if self.group_size == 0:
                self.group_size = 20
                self.group_flag = False

            if self.group_flag or self.coverage_count % 2**9 == 0:
                self.group_flag = True
                self.group_size -= 1
                env_var = f"LLVM_PROFILE_FILE={os.getcwd()}/coverage_data/epoch{self.coverage_count}.profraw"
                cmd = f"{env_var} {cmd}"
            
            self.coverage_count += 1

        try:
            return subprocess.check_output(cmd, shell=True, timeout=5)
        except subprocess.TimeoutExpired as e:
            self.logger.error(e)
            return 'Invalid'
        except subprocess.CalledProcessError as e:
            if int(e.returncode) == 1:
                return 'Invalid'
            self.logger.error(e)
            return None

    def fuzz(self, test_case, thread):
        unique_id = None
        id, grammar = test_case

        output = self.execute(grammar, thread)

        status = self.validate(output)
        if status == 1:
            if unique_id is None:
                curr_time = datetime.now().strftime('%Y.%m.%d-%H:%M:%S')
                unique_id = str(uuid.uuid4()) + '_' + curr_time

            self.commit_test(grammar, unique_id)
            self.coverage.found(id)
        elif status == 0:
            self.coverage.record(id, grammar, self.coverage_paths[thread])
        else:
            self.coverage.invalid(id)

    def validate(self, output):
        if output is 'Invalid':
            return -1
        if output is not None:
            return 0
        return 1
