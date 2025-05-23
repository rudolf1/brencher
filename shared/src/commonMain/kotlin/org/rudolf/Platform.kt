package org.rudolf

interface Platform {
    val name: String
}

expect fun getPlatform(): Platform