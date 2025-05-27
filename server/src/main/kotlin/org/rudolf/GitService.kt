package org.rudolf

import kotlinx.coroutines.*
import org.eclipse.jgit.api.Git
import java.io.File
import java.util.concurrent.ConcurrentHashMap
import kotlin.time.Duration.Companion.minutes

object GitService {
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val repoDir = File("/media/DATA/src/brencher/testState/git-repo")
    private var git: Git? = null
    private val branches = ConcurrentHashMap<String, List<String>>()
    private var repositoryUrl: String = ""
    private var branchRefreshIntervalMinutes: Int = 5
    private var refreshJob: Job? = null

    fun configure(repositoryUrl: String, branchRefreshIntervalMinutes: Int) {
        this.repositoryUrl = repositoryUrl
        this.branchRefreshIntervalMinutes = branchRefreshIntervalMinutes
        initializeRepo()
        startPeriodicRefresh()
    }

    private fun initializeRepo() {
        if (repoDir.exists()) repoDir.deleteRecursively()
        val repoUrl = repositoryUrl.takeIf { it.isNotBlank() } ?: throw IllegalStateException("Git repository not configured")
        git = Git.cloneRepository()
            .setURI(repoUrl)
            .setDirectory(repoDir)
            .call()
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
            repo.fetch().call()
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