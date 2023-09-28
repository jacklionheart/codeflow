//
//  Waveform.swift
//  fantasia
//
//  Created by Jack Heart on 9/28/23.
//

import SwiftUI
import RealmSwift
import AudioKit

struct TrackWaveform: View {
    
    @ObservedRealmObject var track: Track
    
    func audioSamples() -> [Float] {
        let pcmBuffer = track.audioFile().toAVAudioPCMBuffer()!
        
        let channelData = pcmBuffer.floatChannelData?.pointee
        let channelDataCount = Int(pcmBuffer.frameLength)
        return Array(UnsafeBufferPointer(start: channelData, count: channelDataCount))
    }
    
    var body: some View {
        WaveformView(samples:audioSamples())
    }
}

struct WaveformView: View {
    var samples: [Float] = []
    
    // Start and stop positions as ratios (0.0 to 1.0)
    @State private var startPosition: CGFloat = 0.0
    @State private var stopPosition: CGFloat = 1.0
    @State private var draggingMarker: DraggingMarker?

    enum DraggingMarker {
        case start
        case stop
    }
    
    var body: some View {
        GeometryReader { geometry in
            ZStack {
                Path { path in
                    let midY = geometry.size.height / 2
                    let sampleSpacing = geometry.size.width / CGFloat(samples.count)
                    
                    var x: CGFloat = 0.0
                    for sample in samples {
                        path.move(to: CGPoint(x: x, y: midY - CGFloat(sample) * midY))
                        path.addLine(to: CGPoint(x: x, y: midY + CGFloat(sample) * midY))
                        x += sampleSpacing
                    }
                }
                .stroke(Color.blue, lineWidth: 1.0)
                
                // Start marker
                Rectangle()
                    .frame(width: 2)
                    .foregroundColor(.red)
                    .position(x: startPosition * geometry.size.width, y: geometry.size.height / 2)
                    .gesture(
                        DragGesture()
                            .onChanged { value in
                                draggingMarker = .start
                                startPosition = min(max(value.location.x / geometry.size.width, 0), stopPosition)
                            }
                            .onEnded { _ in
                                draggingMarker = nil
                            }
                    )
                
                // Stop marker
                Rectangle()
                    .frame(width: 2)
                    .foregroundColor(.green)
                    .position(x: stopPosition * geometry.size.width, y: geometry.size.height / 2)
                    .gesture(
                        DragGesture()
                            .onChanged { value in
                                draggingMarker = .stop
                                stopPosition = max(min(value.location.x / geometry.size.width, 1), startPosition)
                            }
                            .onEnded { _ in
                                draggingMarker = nil
                            }
                    )
            }
        }
    }
}

struct WaveformView_Previews: PreviewProvider {
    static var previews: some View {
        WaveformView(samples: Array(repeating: 0.5, count: 100))
            .frame(height: 200)
            .padding()
    }
}
//
//struct TrackWaveform_Previews: PreviewProvider {
//    static var previews: some View {
//        TrackWaveform()
//    }
//}
