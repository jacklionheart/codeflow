//
//  SectionPlayer.swift
//  fantasia
//
//  Created by Jack Heart on 7/30/24.
//

import Foundation
import AVFoundation
import Combine

class SectionPlayer: Player {
    // MARK: - Member variables

    var section: Section

    // Internal implementation
    var mixerNode: AVAudioMixerNode
    var trackPlayers: [TrackPlayer] = []
    
   var base: TrackPlayer  {
       return trackPlayers[0]
   }

   var layers: [TrackPlayer] {
       return Array(trackPlayers[1...])
   }
    
    
    func numLoops(layer: TrackPlayer) {
        let baseDuration = base.track.durationSeconds
        let layerDuration = layer.track.durationSeconds
        
        if  layerDuration
        
    }

    var currentPosition : Double {
        subplayers[0].currentPosition
    }
    
    // MARK: - Public Methods

    public func play() {
        // Use a buffer of 50ms in order to sync all tracks.
        let delaySeconds = 0.05
    
        let startTime = AVAudioTime.now() + delaySeconds
        
        for trackPlayer in trackPlayers {
            trackPlayer.schedule(at: startTime, durationSeconds: loopDuration(trackPlayer))
        }
        trackPlayers.forEach { $0.play() }
    }
//    
//    // Stops a track from playing.
//    public func pause() {
//        trackPlayers.forEach { $0.pause() }
//    }
//    
//    public func stop() {
//        trackPlayers.forEach { $0.stop() }
//    }

    override internal func computeCurrentPosition() -> Double {
//        if !playerNode.isPlaying || playerNode.lastRenderTime == nil {
//            return 0.0
//        }
//        
//        let sampleTime = playerNode.playerTime(forNodeTime: playerNode.lastRenderTime!)!.sampleTime
//        let sampleRate = track.format.sampleRate
//        let totalSecs = Double(sampleTime) / sampleRate
//        let result = totalSecs.truncatingRemainder(dividingBy: track.thaw()!.durationSeconds)
//        
//        AppLogger.audio.debug("""
//            Recording.currentPosition
//            sampleTime: \(sampleTime)
//            sampleRate: \(sampleRate)
//            totalSecs: \(totalSecs)
//            result: \(result)
//        """)
//        
        return 0
    }
    
    func receiveNewVolume(_ volume : Double) {
        mixerNode.outputVolume = Float(volume)
    }
    
//    // MARK: - Implementation methods
//    
//    // Each layer restarts on the first (positive, integer) multiple
//    // of the anchor's duration.
//    private func loopDuration(_ layer: ) -> Double {
//        return anchor.track.durationSeconds * ceil(anchor.track.durationSeconds/layer.track.durationSeconds)
//    }
//    
    // MARK: - Initialization
    
    private func subscribeToSubtracks(_ section : Section) {
        let notificationToken = section.thaw()!.observe { [weak self] change in
            switch change {
            case .change(_, let properties):
                for property in properties {
                   if property.name == "subtracks" {
                        DispatchQueue.main.async {
                            self!.stop()
                            
                            self!.trackPlayers = []
                            self!.section.tracks.forEach { track in
                                let trackPlayer = TrackPlayer(track, parent: self!.mixerNode)
                                self!.trackPlayers.append(trackPlayer)
                            }
                        }
                    }
                }
            case .error(let error):
                AppLogger.audio.debug("An error occurred: \(error)")
            case .deleted:
                AppLogger.audio.debug("The object was deleted.")
            }
        }
        
        AnyCancellable {
            notificationToken.invalidate()
        }.store(in: &cancellables)
    }
    
    init(_ section: Section, parent: AVAudioNode) {
        self.section = section
        mixerNode = AVAudioMixerNode()
        mixerNode.outputVolume = Float(section.volume)
        
        super.init(section, parent: parent)

        engine.attach(mixerNode)
        section.tracks.forEach { track in
            let trackPlayer = TrackPlayer(track, parent: mixerNode)
            trackPlayers.append(trackPlayer)
        }
        engine.connect(mixerNode, to: timePitchNode, format: section.format)
        
        subscribeToSubtracks(section)
    }

    deinit {
        stop()
        
        trackPlayers = []
        engine.disconnectNodeInput(mixerNode)
        engine.disconnectNodeOutput(mixerNode)
        engine.detach(mixerNode)
    }
}
