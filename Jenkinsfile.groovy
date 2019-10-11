@Library('common')
import com.typecode.*

node {
  properties([disableConcurrentBuilds()])

  ps = new PipelineSteps()

  ps.checkout()
  deploy()
  test()
  if (env.BRANCH_NAME == 'master') {
    deploy()
    ps.notifySuccess()
  }
}

def test() {
  stage('Test') {
    sh '''
      python3 -m setup.py nosetests
    '''
  }
}

def deploy() {
  stage('Deploy') {
    sh '''
      sudo make install
    '''
    ps.setBuildStatus('Deploy complete', 'SUCCESS')
  }
}
