import Foundation
import AVFoundation
import Combine

class Mix : TrackAudioNode {
    // MARK: - Member variables

    // Initialization paramters
    var track: Track
    var audioEngine: AVAudioEngine
    var parent: AVAudioNode

    // Internal implementation
    var mixerNode: AVAudioMixerNode
    var subtrackAudios: [TrackAudio] = []

    var currentPosition : Double {
        subtrackAudios[0].currentPosition
    }
    
    // MARK: - Public Methods
    
    public func play() {
        subtrackAudios.forEach { $0.play() }
    }
    
    // Stops a track from playing.
    public func pause() {
        subtrackAudios.forEach { $0.pause() }
    }
    
    public func stop() {
        subtrackAudios.forEach { $0.stop() }
    }
    
    func receiveNewVolume(_ volume : Double) {
        mixerNode.outputVolume = Float(volume)
    }
    
    // MARK: - Initialization
    
    init(_ track: Track, parent: AVAudioNode, audioEngine: AVAudioEngine) {
        self.track = track
        self.parent = parent
        self.audioEngine = audioEngine

        mixerNode = AVAudioMixerNode()
        mixerNode.outputVolume = Float(track.volume)
        audioEngine.attach(mixerNode)

        track.subtracks.forEach { subtrack in
            let subtrackAudio = TrackAudio(subtrack, parent: mixerNode, audioEngine: audioEngine)
            subtrackAudios.append(subtrackAudio)
        }
        
        // Connect nodes in a bottom up order
        audioEngine.connect(mixerNode, to: parent, format: track.format)
    }

    deinit {
        subtrackAudios = []
        audioEngine.disconnectNodeInput(mixerNode)
        audioEngine.disconnectNodeOutput(mixerNode)
        audioEngine.detach(mixerNode)
    }
}
