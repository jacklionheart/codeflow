import os

struct AppLogger {
    static let audio = Logger(subsystem: "com.fantasia.ios", category: "audio")
    static let model = Logger(subsystem: "com.fantasia.ios", category: "model")
    static let ui = Logger(subsystem: "com.fantasia.ios", category: "ui")
}
