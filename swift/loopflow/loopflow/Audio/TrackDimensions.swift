//
//  TrackDimensions.swift
//  loopflow
//
//  Created by Jack Heart on 3/21/24.
//
import Foundation
import AVFoundation

struct TrackDimensions {
        
        /** @property pitch
            @abstract cents by which the input signal is pitch shifted
            @discussion
                      1 octave  = 1200 cents
            1 musical semitone  = 100 cents
         
            Range:      -2400 -> 2400
            Default:    0.0
            Unit:       Cents
        */
        let pitch: Float
    
    /** @property pitch
        @abstract cents by which the input signal is pitch shifted
        @discussion
                  1 octave  = 1200 cents
        1 musical semitone  = 100 cents
     
        Range:      -2400 -> 2400
        Default:    0.0
        Unit:       Cents
    */
        let start: Float
        let stop: Float
    
        /** @property rate
            @abstract playback rate of the input signal
         
            Range:      1/32 -> 32.0
            Default:    1.0
            Unit:       Generic
        */
        let playback: Float
    
    init(pitchCents: Float = 0.0, startSecs: Float = 0.0, stopSecs: Float = 0.0, playbackRate: Float = 1.0) {
        self.pitch = pitchCents
        self.start = startSecs
        self.stop = stopSecs
        self.playback = playbackRate
    }
}
