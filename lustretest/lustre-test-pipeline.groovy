pipeline {
    agent {
        label 'lustre-test-agent'
    }

    triggers {
          cron('TZ=Asia/Shanghai\n 0 18 * * *')
    }

    environment {
        CUMULATIVE_RESULT_ID = UUID.randomUUID().toString()
        LUSTRE_BRANCH = "master"
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
                      parameters: [string(name: 'BRANCH', value: 'master'),
                      string(name: 'BUILD_LINUX', value: 'yes'),
                      string(name: 'EXTRA_PATCHES', value: '47004')]
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
                echo 'See test results here: https://testing.whamcloud.com/test_sessions?jobs=lustre-master&user_id=b8340029-197d-4ce0-a8f1-40f76d3bb8c7&builds=${BUILD_ID}#redirect'
            }
        }
    }
}
