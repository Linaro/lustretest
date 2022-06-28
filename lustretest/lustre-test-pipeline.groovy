def maloolink="https://testing.whamcloud.com/test_sessions?jobs=custom&user_id=b8340029-197d-4ce0-a8f1-40f76d3bb8c7&builds=${BUILD_ID}#redirect"
def buildlink="http://213.146.155.72:8080/job/project-lustre-build-release-master/lastBuild/"
def testlogslink="https://uk.linaro.cloud/test-logs/log-${BUILD_ID}/"

pipeline {
    agent {
        label 'lustre-test-agent'
    }

    environment {
        CUMULATIVE_RESULT_ID = UUID.randomUUID().toString()
        LUSTRE_BRANCH = "master"
    }

    options {
        timeout(time: 15, unit: 'HOURS')
    }

    stages {
        stage('Cleanup workspace') {
            steps {
                sh 'ls -l ${WORKSPACE}'
                sh 'rm -fr *'
                sh 'ln -sf /home/centos/workspace/nfs/test_logs ${WORKSPACE}/test_logs'
            }
        }

        stage('Build') {
            steps {
                echo 'Building..'
                build job: 'project-lustre-build-release-master',
                      parameters: [string(name: 'BRANCH', value: "${LUSTRE_BRANCH}")]
            }
        }

        stage('Download scripts') {
            steps {
                sh 'wget -c https://github.com/Linaro/lustretest/archive/refs/heads/main.zip'
                sh 'unzip main.zip'
            }
        }

        stage('Test Execution'){
            parallel {
                stage('Run test group 1') {
                    steps {
                        dir("lustretest-main/lustretest") {
                            sh 'source /home/centos/venv3/bin/activate;python3 test_runner.py 1 false'
                        }
                    }
                }
                stage('Run test group 2') {
                    steps {
                        dir("lustretest-main/lustretest") {
                            sh 'source /home/centos/venv3/bin/activate;python3 test_runner.py 2 false'
                        }
                    }
                }
                stage('Run test group 3') {
                    steps {
                        dir("lustretest-main/lustretest") {
                            sh 'source /home/centos/venv3/bin/activate;python3 test_runner.py 3 false'
                        }
                    }
                }
            }
        }
    }

    post {
        always {
            dir("lustretest-main/lustretest") {
                sh 'source /home/centos/venv3/bin/activate;python3 upload_results.py'
            }
            script {
                def summary = manager.createSummary("package.gif")
                summary.appendText("See <a href=${buildlink}>build job.</a>", false)
                summary.appendText("<br>See <a href=${maloolink}>Maloo test results.</a>", false)
                summary.appendText("<br>See <a href=${testlogslink}>test logs.</a>", false)
            }
        }
    }
}
