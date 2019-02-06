from .call_subprocess import call_subprocess


class DockerCompose():
    DEV_FILE = './docker-compose.yml'
    PROD_FILE = './docker-compose.prod.yml'
    PROD_BUILD_FILE = './docker-compose.prod-build.yml'
    TEST_FILE = './docker-compose.test.yml'

    def __init__(self, file, project):
        self.project = project

    def test(self):
        return DockerCompose(
            file=DockerCompose.TEST_FILE,
            project=self.project + '-test'
        )

    def prod(self):
        return DockerCompose(
            file=DockerCompose.PROD_FILE,
            project=self.project + '-prod'
        )

    def dev(self):
        return DockerCompose(
            file=DockerCompose.DEV_FILE,
            project=self.project + '-dev'
        )

    def run(self, input=[], env={}, target=None, debug=False):
        return call_subprocess(
            ['docker-compose', '-p', self.project, '-f', self.file] + input,
            env=env, target=target, debug=debug
        )
