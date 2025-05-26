package dto

import kotlinx.serialization.Serializable

@Serializable
enum class ReleaseState {
    PAUSE, ACTIVE
}

@Serializable
data class ReleaseDto(
    val name: String,
    val state: ReleaseState,
    val environment: String,
    val branches: List<String>
)