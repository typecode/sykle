@Library('common')
import com.typecode.*

node {
  properties([disableConcurrentBuilds()])

  ps = new PipelineSteps()

  ps.checkout()
  test()
  deploy()
  ps.notifySuccess()
}

def test() {
  stage('Test') {
    sh '''
      python -m unittest discover test "*test.py"
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
