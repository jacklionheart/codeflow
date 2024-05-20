import os

struct AppLogger {
    static let audio = Logger(subsystem: "com.loopflow.ios", category: "audio")
    static let model = Logger(subsystem: "com.loopflow.ios", category: "model")
    static let ui = Logger(subsystem: "com.loopflow.ios", category: "ui")
}
