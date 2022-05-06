pipeline {
    agent {
        label 'lustre-test-agent'
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
                /* 
                build job: 'project-lustre-build-release-master',
                    parameters: [string(name: 'BRANCH', value: 'master'),
                    string(name: 'BUILD_LINUX', value: 'yes')]
                */
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
                stage('Test Suites 1'){
                    stages{
                        stage('Provision test cluster 1') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 provision.py 1 False lustre-wleilf4j'
                                }
                            }
                        }
                        stage('Client node init 1') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 node_init.py 1'
                                }
                            }
                        }
                        stage('Run test suites 1') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 auster.py 1'
                                }
                            }
                        }
                    }
                }
                stage('Test Suites 2'){
                    stages{
                        stage('Provision test cluster 2') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 provision.py 2 False lustre-ghbemii7'
                                }
                            }
                        }
                        stage('Client node init 2') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 node_init.py 2'
                                }
                            }
                        }
                        stage('Run test suites 2') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 auster.py 2'
                                }
                            }
                        }
                    }
                }
                stage('Test Suites 3'){
                    stages{
                        stage('Provision test cluster 3') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 provision.py 3 False lustre-wujqyzn6'
                                }
                            }
                        }
                        stage('Client node init 3') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 node_init.py 3'
                                }
                            }
                        }
                        stage('Run test suites 3') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 auster.py 3'
                                }
                            }
                        }
                    }

                }
            }
        }

    }
}
