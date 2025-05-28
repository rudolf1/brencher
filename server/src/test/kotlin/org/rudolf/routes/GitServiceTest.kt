package org.rudolf.routes

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.runBlocking
import org.eclipse.jgit.api.CreateBranchCommand
import org.eclipse.jgit.api.Git
import org.rudolf.GitService
import java.io.File
import kotlin.test.Test
import kotlin.test.assertTrue

@OptIn(ExperimentalCoroutinesApi::class)
class GitServiceTest {
    @Test
    fun mergeBranchesAndPushAutoBranch_mergesNonConflictingBranchesSuccessfully() = runBlocking {
        // 1. Create a local git repo as the original repo
        val repoDir = File.createTempFile("test-git-remote", "").apply { delete(); mkdir() }
        val git = Git.init()
                .setBare(true)
                .setDirectory(repoDir).call()
        val branch1 = "feature/one"
        val branch2 = "feature/two"
        run {
            val localDir = File.createTempFile("test-git-repo", "").apply { delete(); mkdir() }
            val git = Git.cloneRepository()
                    .setURI(repoDir.toURI().toString())
                    .setDirectory(localDir)
                    .call()
            val file = File(localDir, "file.txt")
            file.writeText("base\n")
            git.add().addFilepattern("file.txt").call()
            git.commit().setMessage("Initial commit").call()

            // 2. Create two branches from the same commit
            git.branchCreate().setName(branch1).setUpstreamMode(CreateBranchCommand.SetupUpstreamMode.SET_UPSTREAM).call()
            git.branchCreate().setName(branch2).setUpstreamMode(CreateBranchCommand.SetupUpstreamMode.SET_UPSTREAM).call()

            // 3. Make non-conflicting changes in each branch
            git.checkout().setName(branch1).call()
            val file1 = File(localDir, "file1.txt")
            file1.writeText("change one\n")
            git.add().addFilepattern("file1.txt").call()
            git.commit().setMessage("Change one").call()

            git.checkout().setName(branch2).call()
            val file2 = File(localDir, "file2.txt")
            file2.writeText("change two\n")
            git.add().addFilepattern("file2.txt").call()
            git.commit().setMessage("Change two").call()
            val res = git.push().setRemote("origin").setPushAll().call()
        }
        // 4. Point GitService to this repo
        GitService.configure(repoDir.toURI().toString(), 5, username = "", password = "")

        // 5. Execute mergeBranchesAndPushAutoBranch for these branches
        val result = org.rudolf.CreateOrGetBranchJob.mergeBranchesAndPushAutoBranch(
            git = org.rudolf.GitService.git,
            branches = listOf(branch1, branch2),
            gitUsername = "",
            gitPassword = ""
        )
        assertTrue(result.isSuccess, "Merge should be successful: ${result.exceptionOrNull()?.message}")
        assertTrue(result.getOrNull()?.first?.startsWith("auto/") == true, "Auto branch should be created")
    }

    @Test
    fun mergeBranchesAndPushAutoBranch_mergesConflictingBranchesSuccessfully() = runBlocking {
        // 1. Create a local git repo as the original repo
        val repoDir = File.createTempFile("test-git-remote", "").apply { delete(); mkdir() }
        val git = Git.init()
                .setBare(true)
                .setDirectory(repoDir).call()
        val branch1 = "feature/one"
        val branch2 = "feature/two"
        run {
            val localDir = File.createTempFile("test-git-repo", "").apply { delete(); mkdir() }
            val git = Git.cloneRepository()
                    .setURI(repoDir.toURI().toString())
                    .setDirectory(localDir)
                    .call()
            val file = File(localDir, "file.txt")
            file.writeText("base\n")
            git.add().addFilepattern("file.txt").call()
            git.commit().setMessage("Initial commit").call()

            // 2. Create two branches from the same commit
            git.branchCreate().setName(branch1).setUpstreamMode(CreateBranchCommand.SetupUpstreamMode.SET_UPSTREAM).call()
            git.branchCreate().setName(branch2).setUpstreamMode(CreateBranchCommand.SetupUpstreamMode.SET_UPSTREAM).call()

            // 3. Make non-conflicting changes in each branch
            git.checkout().setName(branch1).call()
            val file1 = File(localDir, "file1.txt")
            file1.writeText("change one\n")
            git.add().addFilepattern("file1.txt").call()
            git.commit().setMessage("Change one").call()

            git.checkout().setName(branch2).call()
            val file2 = File(localDir, "file1.txt")
            file2.writeText("change two\n")
            git.add().addFilepattern("file1.txt").call()
            git.commit().setMessage("Change two").call()
            val res = git.push().setRemote("origin").setPushAll().call()
        }
        // 4. Point GitService to this repo
        GitService.configure(repoDir.toURI().toString(), 5, username = "", password = "")

        // 5. Execute mergeBranchesAndPushAutoBranch for these branches
        val result = org.rudolf.CreateOrGetBranchJob.mergeBranchesAndPushAutoBranch(
            git = org.rudolf.GitService.git,
            branches = listOf(branch1, branch2),
            gitUsername = "",
            gitPassword = ""
        )
        assertTrue(result.isFailure, "Merge should be failed: ${result.exceptionOrNull()?.message}")
        assertTrue(
                result.exceptionOrNull()?.message?.startsWith("Merge conflict on branch origin/feature/")
                        ?: false,
                "Exception message: ${result.exceptionOrNull()?.message}",
        )
    }

}
