package org.rudolf

import org.eclipse.jgit.api.Git
import java.io.File

object GitService {
    fun fetchBranches(repoUrl: String): List<String> {
        val tempDir = File("temp-repo")
        if (tempDir.exists()) tempDir.deleteRecursively()
        Git.cloneRepository()
            .setURI(repoUrl)
            .setDirectory(tempDir)
            .call()
        return Git.open(tempDir).use {
            it.branchList().call().map { branch -> branch.name }
        }
    }
}