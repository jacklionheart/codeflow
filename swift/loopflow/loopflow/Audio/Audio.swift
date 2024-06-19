import Foundation
import AVFoundation

class Audio : ObservableObject {
    var audioEngine: AVAudioEngine
    @Published public var record: Recorder
    @Published public var trackManager: TrackManager

    func audio(for track: Track) -> TrackAudio {
        return trackManager.audio(for: track)
    }
    
    func stop() {
        return trackManager.stop()
    }
    
    func play(_ trackAudio : TrackAudio) {
        return trackManager.play(trackAudio)
    }
    
    init() {
        audioEngine = AVAudioEngine()
        
        do {
            let audioSession = AVAudioSession.sharedInstance()
            try audioSession.setCategory(.playAndRecord, mode: .default)
            try audioSession.setActive(true)
            try audioSession.setInputGain(1.0)
            AppLogger.model.info("audio.init Active audio session")
        } catch {
            AppLogger.audio.error("audio.init Failed to set up audio session: \(error.localizedDescription)")
        }
        do {
            AppLogger.model.debug("audio.init starting audio engine")
            // Must access the mainMixerNode before starting the engine in order to ensure
            // the engine has the mainMixerNode -> mainOutputNode graph.
            audioEngine.mainMixerNode.outputVolume = 1.0
            try audioEngine.start()
            AppLogger.model.info("audio.init audio engine start successful")
        }
        catch {
            AppLogger.audio.error("audio.init error starting audio engine: \(error)")
        }

        let trackManager = TrackManager(audioEngine: audioEngine)
            self.trackManager = trackManager
        self.record = Recorder(trackManager: trackManager)
    }
}
  

