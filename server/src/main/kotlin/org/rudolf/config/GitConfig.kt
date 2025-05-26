package org.rudolf.config

import kotlinx.serialization.Serializable

@Serializable
data class GitConfig(
    val repositoryUrl: String,
    val branchRefreshIntervalMinutes: Int = 5
)
