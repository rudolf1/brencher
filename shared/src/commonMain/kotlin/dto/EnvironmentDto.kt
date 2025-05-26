package dto

import kotlinx.serialization.Serializable

@Serializable
data class EnvironmentDto(
    val name: String,
    val configuration: String // JSON configuration
)
