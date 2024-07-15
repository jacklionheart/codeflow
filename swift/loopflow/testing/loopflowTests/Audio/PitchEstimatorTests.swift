import XCTest
@testable import loopflow

class PitchEstimatorTests: XCTestCase {

    var pitchEstimator: PitchEstimator!

    override func setUp() {
        super.setUp()
        pitchEstimator = PitchEstimator()
    }

    override func tearDown() {
        pitchEstimator = nil
        super.tearDown()
    }

    // MARK: - Helper Functions

    func generateSineWave(frequency: Float, sampleRate: Float, duration: Float) -> [Float] {
        let numSamples = Int(sampleRate * duration)
        return (0..<numSamples).map { i in
            sin(2 * .pi * frequency * Float(i) / sampleRate)
        }
    }

    func generateComplexWave(frequencies: [Float], amplitudes: [Float], sampleRate: Float, duration: Float) -> [Float] {
        let numSamples = Int(sampleRate * duration)
        return (0..<numSamples).map { i in
            frequencies.enumerated().reduce(0) { sum, element in
                let (index, freq) = element
                return sum + amplitudes[index] * sin(2 * .pi * freq * Float(i) / sampleRate)
            }
        }
    }

    // MARK: - Step 2 Tests

    func testAutocorrelationWithSimpleSignal() {
        let signal: [Float] = [1, 2, 3, 4, 5]
        let result = pitchEstimator.autocorrelation(signal: signal)
        
        let expected: [Float] = [55, 40, 26, 14, 5]
        
        XCTAssertEqual(result.count, signal.count, "Result should have the same length as the input signal")
        
        for (index, value) in result.enumerated() {
            XCTAssertEqual(value, expected[index], "Mismatch at index \(index)")
        }
    }
    
    func testDifferenceFunction() {
        let input = generateSineWave(frequency: 440, sampleRate: 44100, duration: 0.1)
        let diff = pitchEstimator.differenceFunction(input: input)
        
        // The difference function should have a minimum near the period of the sine wave
        let expectedPeriod = Int(44100 / 440)
        
        // Find all local minima
        var localMinima: [(index: Int, value: Float)] = []
        for i in 1..<diff.count-1 {
            if diff[i] < diff[i-1] && diff[i] < diff[i+1] {
                localMinima.append((i, diff[i]))
            }
        }
        
        // Sort local minima by their values
        localMinima.sort { $0.value < $1.value }
        
        // Print out the first few minima for debugging
        print("Expected period: \(expectedPeriod)")
        print("First few minima (period, value):")
        for i in 0..<min(10, localMinima.count) {
            print("\(i), \(localMinima[i])")
        }
        
        // Check if any of the first few minima are close to the expected period
        let foundExpectedMinimum = localMinima.prefix(5).contains { abs($0.index - expectedPeriod) <= 2 }
        XCTAssertTrue(foundExpectedMinimum, "No minimum found near the expected period")
        
        // Print values around expected period
        print("Values around expected period:")
        for i in max(0, expectedPeriod - 5)...min(diff.count - 1, expectedPeriod + 5) {
            print("period: \(i), value: \(diff[i])")
        }
    }

    // MARK: - Step 3 Tests

    func testCumulativeMeanNormalizedDifference() {
        let input = generateSineWave(frequency: 440, sampleRate: 44100, duration: 0.1)
        let diff = pitchEstimator.differenceFunction(input: input)
        let cmnd = pitchEstimator.cumulativeMeanNormalizedDifference(diff: diff)
        
        // Existing assertion
        XCTAssertEqual(cmnd[0], 1)
        
        // (a) Assert that the value of cmnd at 100 is < 0.1
        XCTAssertLessThan(cmnd[100], 0.1, "CMND value at index 100 should be less than 0.1")
        
        // (b) Assert that the value at cmnd reaches a minimum near 100
        let minIndex = cmnd.indices.min(by: { cmnd[$0] < cmnd[$1] })!
        XCTAssertTrue(abs(minIndex - 100) < 5, "Minimum CMND should be near index 100")
        
        // (c) Assert that the value of cmnd at index 100 is close to the absolute minimum
        let minValue = cmnd.min()!
        XCTAssertTrue(abs(cmnd[100] - minValue) < 0.01, "CMND at index 100 should be close to the minimum value")
    }
    
    // MARK: - Step 4 Tests

    func testFirstPeriodBelowThreshold() {
        let input = generateSineWave(frequency: 440, sampleRate: 44100, duration: 0.1)
        let diff = pitchEstimator.differenceFunction(input: input)
        let cmnd = pitchEstimator.cumulativeMeanNormalizedDifference(diff: diff)
        let period = pitchEstimator.firstPeriodBelowThreshold(cmnd: cmnd)
        
        XCTAssertNotNil(period)
        if let period = period {
            let expectedPeriod = Int(44100 / 440)
            XCTAssertEqual(period, expectedPeriod, accuracy: 10)
        }
    }

    // MARK: - Step 5 Tests

    func testInterpolatePitchPeriod() {
        let input = generateComplexWave(frequencies: [440, 880], amplitudes: [1, 0.5], sampleRate: 44100, duration: 0.1)
        let diff = pitchEstimator.differenceFunction(input: input)
        let cmnd = pitchEstimator.cumulativeMeanNormalizedDifference(diff: diff)
        let period = pitchEstimator.firstPeriodBelowThreshold(cmnd: cmnd)!
        let interpolatedPeriod = pitchEstimator.interpolatePitchPeriod(cmnd: cmnd, tau: period)
        
        let expectedPeriod = 44100 / 440
        XCTAssertEqual(interpolatedPeriod, Float(expectedPeriod), accuracy: 2.0)
    }

    // MARK: - End-to-End Tests

    func testEstimatePeriodForSineWave() {
        let input = generateSineWave(frequency: 440, sampleRate: 44100, duration: 0.1)
        let estimatedPeriod = pitchEstimator.estimatePeriod(input)
        
        XCTAssertNotNil(estimatedPeriod)
        if let estimatedPeriod = estimatedPeriod {
            let expectedPeriod = 44100 / 440
            XCTAssertEqual(estimatedPeriod, Float(expectedPeriod), accuracy: 2.5)
        }
    }

    func testEstimatePeriodForComplexWave() {
        let input = generateComplexWave(frequencies: [440, 880], amplitudes: [1, 0.5], sampleRate: 44100, duration: 0.1)
        let estimatedPeriod = pitchEstimator.estimatePeriod(input)
        
        XCTAssertNotNil(estimatedPeriod)
        if let estimatedPeriod = estimatedPeriod {
            let expectedPeriod = 44100 / 440 // Should detect the fundamental frequency
            XCTAssertEqual(estimatedPeriod, Float(expectedPeriod), accuracy: 2.5)
        }
    }
}
