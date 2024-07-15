//
//  Pitch.swift
//  loopflow
//
//  Created by Jack Heart on 7/11/24.
//

import Foundation

public struct Pitch: Equatable, Comparable {
    public enum NoteName: String, CaseIterable {
        case C, CSharp, D, DSharp, E, F, FSharp, G, GSharp, A, ASharp, B
        
        public var displayName: String {
           switch self {
           case .CSharp: return "C♯"
           case .DSharp: return "D♯"
           case .FSharp: return "F♯"
           case .GSharp: return "G♯"
           case .ASharp: return "A♯"
           default: return rawValue
           }
       }
    
        public var flatName: String {
            switch self {
            case .CSharp: return "D♭"
            case .DSharp: return "E♭"
            case .FSharp: return "G♭"
            case .GSharp: return "A♭"
            case .ASharp: return "B♭"
            default: return rawValue
            }
        }
    }
    
    public let hz: Double
    public let noteName: NoteName
    public let octave: Int
    public let cents: Double
    
    public var midiNoteNumber: Int {
        return Int(round(12 * log2(hz / 440) + 69))
    }
    
    public init(_ hz: Double) {
        self.hz = hz
        let midiNote = 12 * log2(hz / 440) + 69
        let midiNoteRounded = round(midiNote)
        
        self.cents = 100 * (midiNote - midiNoteRounded)
        self.octave = Int((midiNoteRounded - 12) / 12)
        
        let noteIndex = Int(midiNoteRounded) % 12
        self.noteName = NoteName.allCases[noteIndex]
    }
    
    public init(midiNoteNumber: Int) {
        let hz = 440 * pow(2, (Double(midiNoteNumber) - 69) / 12)
        self.init(hz)
    }
    
    public init(noteName: NoteName, octave: Int) {
        let midiNoteNumber = NoteName.allCases.firstIndex(of: noteName)! + (octave + 1) * 12
        self.init(midiNoteNumber: midiNoteNumber)
    }
    
    public var fullName: String {
        return "\(noteName.displayName)\(octave)"
    }
    
    public static func < (lhs: Pitch, rhs: Pitch) -> Bool {
        return lhs.hz < rhs.hz
    }
    
    public static let standardTuning = 440.0
}
