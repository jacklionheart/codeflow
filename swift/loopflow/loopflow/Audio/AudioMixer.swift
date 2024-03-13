import Foundation
import AVFoundation

class AudioMixer: ObservableObject {
    
    var audioEngine: AVAudioEngine
    @Published var audioNodes: [UInt64: AudioNode]
    @Published var activeAudioNodes: [UInt64: AudioNode]
    
    // MARK: - Public Methods
    
    /// Plays a track. Stop all other tracks. Restarts the track from beginning if already playing.
    public func play(_ track : Track) {
        let audioNode = audioNode(track)
        let playerNode = audioNode.playerNode
        
        stopAllTracks()
        self.loop(playerNode, from: track)
        playerNode.play()
        shiftPitch(of: track, by: track.semitoneShift)
        activeAudioNodes[track.id] = audioNode
    }
    
    /// Stops a track from playing.
    public func stop(_ track : Track) {
        if let audioNode = activeAudioNodes[track.id] {
            audioNode.playerNode.stop()
            activeAudioNodes[track.id] = nil
       }
    }
    
    /// Stops all tracks from playing.
    public func stopAllTracks() {
        for (_, audioNode) in activeAudioNodes {
            audioNode.playerNode.stop()
        }
        activeAudioNodes.removeAll()
    }
    
    /// Returns True iff a track is actively playing.
    public func isPlaying(_ track: Track) -> Bool {
        return activeAudioNodes[track.id] != nil
    }
    
    /// Shift the pitch of a track.
    public func shiftPitch(of track: Track, by semitones: Int) {
        let audioNode = audioNode(track)
        audioNode.pitchNode.pitch = Float(semitones) * 100.0
    }
    
    // MARK: - Initialization

    init() {
        audioEngine = AVAudioEngine()
        audioNodes = [:]
        activeAudioNodes = [:]
        
        print("init Audio Mixer")
        
        // A Silent Buffer is a hack to avoid an empty engine which can cause problems.
        let silentPlayerNode = AVAudioPlayerNode()
        audioEngine.attach(silentPlayerNode)
        let silentFormat = AVAudioFormat(standardFormatWithSampleRate: 44100, channels: 2)!
        let silentBuffer = AVAudioPCMBuffer(pcmFormat: silentFormat, frameCapacity: AVAudioFrameCount(silentFormat.sampleRate * 0.5))!
        silentBuffer.frameLength = silentBuffer.frameCapacity
        audioEngine.connect(silentPlayerNode, to: audioEngine.mainMixerNode, format: silentBuffer.format)
        audioEngine.connect(audioEngine.mainMixerNode, to: audioEngine.outputNode, format: nil)

        print("connected mixer node")
        do {
            print("starting audio engine")
            try audioEngine.start()
            print("playing silent buffer")
            playSilentBuffer(silentPlayerNode: silentPlayerNode, silentBuffer: silentBuffer)
        } catch {
            print("Error starting audio engine: \(error)")
        }
        
        print("audio engine is running: \(audioEngine.isRunning)")
    }
    
    // MARK: - Private Methods
    
    private func playSilentBuffer(silentPlayerNode : AVAudioPlayerNode, silentBuffer : AVAudioPCMBuffer) {
        // Play the silent buffer in loop
        silentPlayerNode.scheduleBuffer(silentBuffer) {
            self.playSilentBuffer(silentPlayerNode: silentPlayerNode, silentBuffer: silentBuffer)
        }
        silentPlayerNode.play()
    }
    
    /// Loops a track by scheduling it to
    private func loop(_ playerNode : AVAudioPlayerNode, from track : Track) {
        let audioFile = track.audioFile()
        let sampleRate = audioFile.processingFormat.sampleRate
        let startSample = AVAudioFramePosition(track.startSeconds * sampleRate)
        let endSample = AVAudioFramePosition((track.startSeconds + track.durationSeconds) * sampleRate)
        let frameCount = AVAudioFrameCount(endSample - startSample)
        let trackURL = track.sourceURL
        let trackName = track.name

        print("""
               --- Playing track ---
               Track name: \(trackName)
               Track location: \(trackURL)
               Sample Rate: \(sampleRate)
               Start Sample: \(startSample)
               End Sample: \(endSample)
               Frame Count: \(frameCount)
               -------------------------------
               """)
        
        playerNode.scheduleSegment(audioFile, startingFrame: startSample, frameCount: frameCount, at: nil) {
            self.loop(playerNode, from: track)
        }
    }
    private func audioNode(_ track : Track) -> AudioNode {
        let tid = track.id
        if audioNodes[tid] == nil {
            let playerNode = AVAudioPlayerNode()
            let pitchNode = AVAudioUnitTimePitch()

            audioEngine.attach(playerNode)
            audioEngine.attach(pitchNode)

            audioNodes[tid] = AudioNode(playerNode: playerNode, pitchNode: pitchNode)
            audioEngine.connect(playerNode, to: pitchNode, format: track.audioFile().processingFormat)
            audioEngine.connect(pitchNode, to: audioEngine.mainMixerNode, format: track.audioFile().processingFormat)

        }
        return audioNodes[tid]!
    }
    
}

struct AudioNode {
    let playerNode: AVAudioPlayerNode
    let pitchNode: AVAudioUnitTimePitch
    
    init(playerNode: AVAudioPlayerNode, pitchNode: AVAudioUnitTimePitch) {
        self.playerNode = playerNode
        self.pitchNode = pitchNode
    }
}
