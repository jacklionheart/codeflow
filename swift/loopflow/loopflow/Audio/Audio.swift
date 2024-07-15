import Foundation
import AVFoundation

class Audio : ObservableObject {
    var audioEngine: AVAudioEngine
    @Published public var record: Recorder
    @Published public var trackManager: TrackSingleton

    func audio(for track: Track) -> TrackAudio {
        return trackManager.audio(for: track)
    }
    
    func pause() {
        return trackManager.pause()
    }
    
    func play(_ trackAudio : TrackAudio) {
        return trackManager.play(trackAudio)
    }
    
    init() {
        audioEngine = AVAudioEngine()
        
        do {
            let audioSession = AVAudioSession.sharedInstance()
            try audioSession.setCategory(.playAndRecord, mode: .default)
            try audioSession.setPreferredSampleRate(44100)
            try audioSession.setPreferredIOBufferDuration(0.005)
            try audioSession.setActive(true)
            try audioSession.setInputGain(1.5)
            AppLogger.model.info("audio.init Active audio session")
            print("inputFormat: \(audioEngine.inputNode.inputFormat(forBus: 0))")
            print("outputFormat: \(audioEngine.inputNode.outputFormat(forBus: 0))")

        } catch {
            AppLogger.audio.error("audio.init Failed to set up audio session: \(error.localizedDescription)")
        }
        do {
            AppLogger.model.debug("audio.init starting audio engine")
            // Must access the mainMixerNode before starting the engine in order to ensure
            // the engine has the mainMixerNode -> mainOutputNode graph.
            audioEngine.mainMixerNode.outputVolume = 1.0
            try audioEngine.start()
            print("after startung inputFormat: \(audioEngine.inputNode.inputFormat(forBus: 0))")
            print("after starting outputFormat: \(audioEngine.inputNode.outputFormat(forBus: 0))")

            AppLogger.model.info("audio.init audio engine start successful")
        }
        catch {
            AppLogger.audio.error("audio.init error starting audio engine: \(error)")
        }

        let trackManager = TrackSingleton(audioEngine: audioEngine)
        self.trackManager = trackManager
        self.record = Recorder(audioEngine: audioEngine, trackManager: trackManager)
    }
}
  

