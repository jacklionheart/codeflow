//
//  PitchEstimator.swift
//  fantasia
//
//  Created by Jack Heart on 7/11/24.
//

import Foundation
import AVFoundation
import Accelerate

// Uses the YIN algoritm
public class PitchEstimator {
    // The maximum period (corresponding to lowest frequency) we want to detect, in samples
    private let maxPeriod: Int
    // The minimum period (corresponding to highest frequency) we want to detect, in samples
    private let minPeriod: Int
    // We will estimate the period to be the smallest period whose score goes below this threshold (See step 4).
    private let threshold: Double
    
    
    public init(minPeriod: Int = 10, maxPeriod: Int = 2048, threshold: Double = 0.1) {
        self.threshold = threshold
        self.minPeriod = minPeriod // 10 samples is ~4.4khz at 44.1khz sample rate
        self.maxPeriod = maxPeriod // 2048 samples is ~21hz at 44.1khz sample rate
    }
    
    public func minimumSamplesSize() -> Int {
        return 2 * maxPeriod
    }
    
    public func estimate(_ buffer: AVAudioPCMBuffer) -> Pitch? {
        guard let channelData = buffer.floatChannelData else {
            AppLogger.audio.error("Error: Could not get channel data from buffer")
            return nil
        }
        
        let frameLength = Int(buffer.frameLength)
        let sampleRate = buffer.format.sampleRate
        assert(sampleRate == 44100.0 || sampleRate == 48000)
        
        // If stereo, we'll just use the left channel for now.
        let samples = Array(UnsafeBufferPointer(start: channelData[0], count: frameLength))
        
        if let detectedPeriod = estimatePeriod(samples) {
            return Pitch(sampleRate / Double(detectedPeriod))
        }
        
        AppLogger.audio.error("Error: Could not detect pitch")
        return nil
    }
    
    public func estimatePeriod(_ input: [Float]) -> Float? {
        // Note: No Step 1; that is just theoretical background.
        
        // Step 2
        let diff = differenceFunction(input: input)
        
        // Step 3
        let cmnd = cumulativeMeanNormalizedDifference(diff: diff)
        
        // Step 4
        let integralPeriod = firstPeriodBelowThreshold(cmnd: cmnd)
        if integralPeriod == nil {
            return nil
        }
        
        // Step 5
        return interpolatePitchPeriod(cmnd: cmnd, tau: integralPeriod!)
        
        // TODO: Step 6: localSearch
    }
    
    internal func autocorrelation(signal: [Float]) -> [Float] {
        let n = signal.count
        
        let paddedSignal = signal + [Float](repeating: 0, count: n)
        let result = vDSP.correlate(paddedSignal, withKernel: signal)
        
        return Array(result)
    }

    
    // Implements Step 2 of YIN
    // Returns an array of difference values for each period in [0, maxPeriod].
    internal func differenceFunction(input: [Float]) -> [Float] {
        var diff = [Float](repeating: 0, count: maxPeriod+1)
        
        
        // Calcuate r_t(tau), i.e. the ACF of the input
        let rt = autocorrelation(signal: input)
        print("rt count: \(rt.count) in")
        
        // Calcualte r_(t+tau)(0) by initializing to the full sum, then remove a term each time
        let squaredEnergies = vDSP.square(input)
        // Initialize to full ACF
        var runningRtTau0 = rt[0]
        
        for tau in 1...maxPeriod {
            // r-(t+tau)(0) = r_(t+tau-1)(0) - input(tau-1)^2
            runningRtTau0 = runningRtTau0 - squaredEnergies[tau-1]
            
            // Compute d_t(tau) = r_t(0) + r_(t+tau)(0) - 2r_t(tau)
            diff[tau] = rt[0] + runningRtTau0 - 2 * rt[tau]
        }
        
        return diff
    }
    

    // Implements Step 3 of YIN
    // Returns an array of cumulative mean normalized difference values for each period between [0, maxPeriod].
    internal func cumulativeMeanNormalizedDifference(diff: [Float]) -> [Float] {
        var cmnd = [Float](repeating: 1, count: maxPeriod + 1)
        
        // Calculate cumulative sum of diff
        let cumulativeSum = vDSP.integrate(diff, using: .runningSum)
        print("diff: \(diff[0..<10])")
        print("sum (integration): \(cumulativeSum[0..<10])")
        // Calculate CMNDF for tau from 1 to maxPeriod
        for tau in 1...maxPeriod {
            if (tau == 1) {
                print("""
                tau: \(tau),
                diff: \(diff[tau]),
                cumSum: \(cumulativeSum[tau]),
                """)
            }
            cmnd[tau] = diff[tau] / (cumulativeSum[tau] / Float(tau))
        }
        
        return cmnd
    }
    
    // Implements Step 4 of YIN
    // Finds the first period where the CMND fo that period is below the threshhold
    internal func firstPeriodBelowThreshold(cmnd: [Float]) -> Int? {
        
        for tau in minPeriod...maxPeriod {
            if cmnd[tau] < Float(threshold) {
                return tau
            }
        }
        
        return nil
    }
    
    // Implements Step 5 of YIN
    // Fits a parabola around the CMND to find a non-integer period
    // that may fit the data better.
    internal func interpolatePitchPeriod(cmnd: [Float], tau: Int) -> Float {
        let y1 = Float(cmnd[tau - 1])
        let y2 = Float(cmnd[tau])
        let y3 = Float(cmnd[tau + 1])
        
        let a = y1 + y3 - 2 * y2
        let b = (y3 - y1) / 2
        
        if a == 0 {
            return Float(tau)
        }
        
        let betterTau = Float(tau) - b / (2 * a)
        return max(Float(minPeriod), min(Float(maxPeriod), betterTau))
    }
}
