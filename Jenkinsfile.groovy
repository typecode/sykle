@Library('common')
import com.typecode.*

node {
  properties([disableConcurrentBuilds()])
  
  ps = new PipelineSteps()
  
  ps.checkout()
  deploy()
  ps.notifySuccess()
}

def deploy() {
  stage('Deploy') {
    sh '''
      sudo make install
    '''
    ps.setBuildStatus('Deploy complete', 'SUCCESS')
  }
}