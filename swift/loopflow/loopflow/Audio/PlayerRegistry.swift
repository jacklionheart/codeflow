//
//  PlayerRegistry.swift
//  loopflow
//
//  Created by Jack Heart on 6/11/24.
//

import Foundation
import AVFoundation

class PlayerRegistry : ObservableObject {
    var engine: AVAudioEngine
    
    @Published public var currentPlayer: Player?
    
    private var playerCache: [UInt64: Player] = [:]
    
    func player(for loop: Loop) -> Player {
        if let cachedPlayer = playerCache[loop.id] {
            return cachedPlayer
        } else {
            let player = loop.createPlayer(parent: engine.mainMixerNode)
            playerCache[loop.id] = player
            return player
        }
    }
    
    func stopCurrent() {
        if currentPlayer != nil {
            currentPlayer!.stop()
            currentPlayer = nil
        }
    }
    
    func play(_ player : Player) {
        if player != currentPlayer {
            if currentPlayer != nil {
                currentPlayer!.stop()
            }
            currentPlayer = player
        }
        currentPlayer!.play()
    }
    
    init(engine: AVAudioEngine) {
        self.engine = engine
    }
}
