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

    /**
     * Checks if the auto/<hash> branch is up-to-date with the selected branches.
     * Returns true if up-to-date, false otherwise.
     */
    private fun isAutoBranchUpToDate(branches: List<String>): Boolean {
        val repo = git ?: return false
        if (branches.isEmpty()) return false
        val sortedBranches = branches.sorted()
        val hash = java.security.MessageDigest.getInstance("SHA-1")
            .digest(sortedBranches.joinToString(",").toByteArray())
            .joinToString("") { "%02x".format(it) }
        val autoBranch = "auto/$hash"
        val autoRef = repo.repository.findRef(autoBranch) ?: return false
        // Compare the commit of auto/<hash> with a synthetic merge of all selected branches
        // If the tip of auto/<hash> is a merge commit with all selected branches as parents, consider it up-to-date
        val revWalk = org.eclipse.jgit.revwalk.RevWalk(repo.repository)
        val autoCommit = revWalk.parseCommit(autoRef.objectId)
        val parentIds = autoCommit.parents.map { it.name }.sorted()
        val branchHeads = sortedBranches.mapNotNull { repo.repository.findRef(it)?.objectId?.name }
        revWalk.close()
        return parentIds == branchHeads
    }

    /**
     * Merges the given branches, creates/updates auto/<hash> branch, and pushes to remote.
     * Returns the name of the auto branch or error message.
     */
    suspend fun mergeBranchesAndPushAutoBranch(branches: List<String>): Result<String> = withContext(Dispatchers.IO) {
        val repo = git ?: return@withContext Result.failure(Exception("Git repo not initialized"))
        if (branches.isEmpty()) return@withContext Result.failure(Exception("No branches specified"))
        val sortedBranches = branches.sorted()
        val hash = java.security.MessageDigest.getInstance("SHA-1")
            .digest(sortedBranches.joinToString(",").toByteArray())
            .joinToString("") { "%02x".format(it) }
        val autoBranch = "auto/$hash"
        val tempBranch = "temp-merge-$hash"
        try {
            // Fetch latest
            repo.fetch().call()
            if (isAutoBranchUpToDate(branches)) {
                return@withContext Result.success(autoBranch) // Already up-to-date, do nothing
            }
            // Delete temp branch if exists
            repo.repository.findRef(tempBranch)?.let {
                repo.branchDelete().setBranchNames(tempBranch).setForce(true).call()
            }
            // Create temp branch from first branch
            repo.checkout().setName(sortedBranches[0]).call()
            repo.branchCreate().setName(tempBranch).setForce(true).call()
            repo.checkout().setName(tempBranch).call()
            // Merge other branches
            for (branch in sortedBranches.drop(1)) {
                val mergeResult = repo.merge()
                    .include(repo.repository.findRef(branch))
                    .call()
                if (!mergeResult.mergeStatus.isSuccessful) {
                    // Clean up temp branch
                    repo.checkout().setName(sortedBranches[0]).call()
                    repo.branchDelete().setBranchNames(tempBranch).setForce(true).call()
                    return@withContext Result.failure(Exception("Merge conflict on branch $branch: ${mergeResult.toString()}"))
                }
            }
            // Create or update auto/<hash> branch
            repo.branchCreate().setName(autoBranch).setForce(true).call()
            repo.checkout().setName(autoBranch).call()
            // Push auto branch
            repo.push().setRemote("origin").add(autoBranch).setForce(true).call()
            // Clean up temp branch
            repo.checkout().setName(sortedBranches[0]).call()
            repo.branchDelete().setBranchNames(tempBranch).setForce(true).call()
            return@withContext Result.success(autoBranch)
        } catch (e: Exception) {
            return@withContext Result.failure(e)
        }
    }
}