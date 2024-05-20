import Foundation
import AVFoundation

class Audio : ObservableObject {
    var engine: AVAudioEngine
    @Published public var record: Recorder
    @Published public var play: Player
    
    init() {
        engine = AVAudioEngine()
        
        do {
            let audioSession = AVAudioSession.sharedInstance()
            try audioSession.setCategory(.playAndRecord, mode: .default)
            try audioSession.setActive(true)
            AppLogger.model.info("audio.init Active audio session")
        } catch {
            AppLogger.audio.error("audio.init Failed to set up audio session: \(error.localizedDescription)")
        }
        do {
            AppLogger.model.debug("audio.init starting audio engine")
            // Must access the mainMixerNode before starting the engine in order to ensure
            // the engine has the mainMixerNode -> mainOutputNode graph.
            engine.mainMixerNode.outputVolume = 1.0
            try engine.start()
            AppLogger.model.info("audio.init audio engine start successful")
        }
        catch {
            AppLogger.audio.error("audio.init error starting audio engine: \(error)")
        }

        record = Recorder()
        play = Player(engine)
    }
}
  
