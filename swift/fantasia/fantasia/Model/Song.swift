//
//  Song.swift
//  fantasia
//
//  Created by Jack Heart on 7/23/24.
//

import Foundation
//
//  Track.swift
//  fantasia
//
//  Created by Jack Heart on 4/19/23.
//

import Foundation
import RealmSwift
import AVFoundation
import Accelerate

class Song: Loop {
    
    // MARK: Persisted values
    @Persisted var sections = RealmSwift.List<Section>()
    
    // MARK: Computed values
    
    
    override var format: AVAudioFormat {
        // TODO: ???
        return sections[0].format
    }
    
    override var sourceAmplitudes : [CGFloat] {
        return sections.reduce(into: [CGFloat]()) { result, section in
            result.append(contentsOf: section.amplitudes)
        }
    }
    
    override var sourceStopSeconds : Double {
        return sections.reduce(into: 0.0) { result, section in
            result += section.durationSeconds
        }
    }
//    
//    override func createPlayer(parent: AVAudioNode) -> Player {
//        let engine = parent.engine
//        return SongPlayer(song, parent: parent)
//    }
        
    // MARK: Initializers
    
    convenience init(name: String) {
        self.init()
        self.name = name + " Song"
    }
    
    public func addSection(_ section: Section) {
        sections.append(section)
        section.song = self
    }
    
    
}



