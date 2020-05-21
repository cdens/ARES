node {
    properties([
            [$class: 'ScannerJobProperty', doNotScan: false],
            [$class: 'ThrottleJobProperty', categories: [], limitOneJobWithMatchingParams: false, maxConcurrentPerNode: 0, maxConcurrentTotal: 0, paramsToUseForLimit: '', throttleEnabled: false, throttleOption: 'project'],
            pipelineTriggers([snapshotDependencies(), pollSCM('')])
    ])
    stage('SCM') {
        checkout([$class: 'GitSCM', branches: [[name: '*/master']], doGenerateSubmoduleConfigurations: false, extensions: [[$class: 'SubmoduleOption', disableSubmodules: false, parentCredentials: true, recursiveSubmodules: true, reference: '', trackingSubmodules: true]], gitTool: 'Default', submoduleCfg: [], userRemoteConfigs: [[credentialsId: 'b901ff19-3484-442d-bc11-f6b3f2be7d26', url: 'https://bitbucket.di2e.net/scm/axbt/axbt.git']]])
    }
    stage('SonarQube Analysis') {
        withSonarQubeEnv("Sonarqube Di2e Server") {
            def sonarScanner = tool name: 'SonarQube Scanner', type: 'hudson.plugins.sonar.SonarRunnerInstallation'
            def scannerHome = tool 'SonarScanner 4.0';
            sh "${scannerHome}/bin/sonar-scanner -Dsonar.projectKey=AXBT -Dsonar.sources=."
        }
    }

}
