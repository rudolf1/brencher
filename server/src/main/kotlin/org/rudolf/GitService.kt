package org.rudolf

import kotlinx.coroutines.*
import org.eclipse.jgit.api.Git
import java.io.File
import java.util.concurrent.ConcurrentHashMap
import kotlin.time.Duration.Companion.minutes

object GitService {
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val repoDir = File("/media/DATA/src/brencher/testState/git-repo")
    var git: Git? = null
    private val branches = ConcurrentHashMap<String, List<String>>()
    private var repositoryUrl: String = ""
    private var branchRefreshIntervalMinutes: Int = 5
    private var refreshJob: Job? = null
    private var gitUsername: String = ""
    private var gitPassword: String = ""

    fun configure(repositoryUrl: String, branchRefreshIntervalMinutes: Int, username: String, password: String) {
        this.repositoryUrl = repositoryUrl
        this.branchRefreshIntervalMinutes = branchRefreshIntervalMinutes
        this.gitUsername = username
        this.gitPassword = password
        initializeRepo()
        startPeriodicRefresh()
    }

    private fun initializeRepo() {
        if (repoDir.exists()) repoDir.deleteRecursively()
        val repoUrl = repositoryUrl.takeIf { it.isNotBlank() } ?: throw IllegalStateException("Git repository not configured")
        val cloneCommand = Git.cloneRepository()
            .setURI(repoUrl)
            .setDirectory(repoDir)
        if (gitUsername.isNotBlank() && gitPassword.isNotBlank()) {
            val credentialsProvider = org.eclipse.jgit.transport.UsernamePasswordCredentialsProvider(gitUsername, gitPassword)
            cloneCommand.setCredentialsProvider(credentialsProvider)
        }
        git = cloneCommand.call()
        refreshBranches()
    }

    private fun startPeriodicRefresh() {
        refreshJob?.cancel()
        refreshJob = scope.launch {
            while (isActive) {
                delay(branchRefreshIntervalMinutes.minutes)
                refreshBranches()
            }
        }
    }

    private fun refreshBranches() {
        git?.let { repo ->
            val fetchCommand = repo.fetch()
            if (gitUsername.isNotBlank() && gitPassword.isNotBlank()) {
                val credentialsProvider = org.eclipse.jgit.transport.UsernamePasswordCredentialsProvider(gitUsername, gitPassword)
                fetchCommand.setCredentialsProvider(credentialsProvider)
            }
            fetchCommand.call()
            val branchList = repo.branchList().setListMode(org.eclipse.jgit.api.ListBranchCommand.ListMode.REMOTE).call()
            branches[repositoryUrl] = branchList.map { ref ->
                ref.name.removePrefix("refs/remotes/origin/")
            }
        }
    }
    
    fun fetchBranches(repoUrl: String = repositoryUrl): List<String> {
        return branches[repoUrl] ?: emptyList()
    }
}