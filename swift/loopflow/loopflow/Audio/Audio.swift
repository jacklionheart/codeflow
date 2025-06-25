import Foundation
import AVFoundation

class Audio: ObservableObject {
    var engine: AVAudioEngine
    var playerRegistry: PlayerRegistry
    @Published public var record: Recorder

    func player(for loop: Loop) -> Player {
        return playerRegistry.player(for: loop)
    }
    
    func stop() {
        return playerRegistry.stopCurrent()
    }
    
    func play(player: Player) {
        return playerRegistry.play(player)
    }
    
    init() {
        engine = AVAudioEngine()
        
        do {
            let audioSession = AVAudioSession.sharedInstance()
            try audioSession.setCategory(.playAndRecord, mode: .default)
            try audioSession.setPreferredSampleRate(44100)
            try audioSession.setPreferredIOBufferDuration(0.005)
            try audioSession.setActive(true)
            try audioSession.setInputGain(1.5)
            AppLogger.model.info("audio.init Active audio session")
            print("inputFormat: \(engine.inputNode.inputFormat(forBus: 0))")
            print("outputFormat: \(engine.inputNode.outputFormat(forBus: 0))")

        } catch {
            AppLogger.audio.error("audio.init Failed to set up audio session: \(error.localizedDescription)")
        }
        do {
            AppLogger.model.debug("audio.init starting audio engine")
            // Must access the mainMixerNode before starting the engine in order to ensure
            // the engine has the mainMixerNode -> mainOutputNode graph.
            engine.mainMixerNode.outputVolume = 1.0
            try engine.start()
            print("after startung inputFormat: \(engine.inputNode.inputFormat(forBus: 0))")
            print("after starting outputFormat: \(engine.inputNode.outputFormat(forBus: 0))")

            AppLogger.model.info("audio.init audio engine start successful")
        }
        catch {
            AppLogger.audio.error("audio.init error starting audio engine: \(error)")
        }

        self.playerRegistry = PlayerRegistry(engine: engine)
        self.record = Recorder(engine: engine, playerRegistry: playerRegistry)
    }
}
  

