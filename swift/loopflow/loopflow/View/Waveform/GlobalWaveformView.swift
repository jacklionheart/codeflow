import SwiftUI

struct GlobalWaveformView: View {
    @ObservedObject var trackAudio: TrackAudio
    
    let barWidth: CGFloat = 1
    let barSpacing: CGFloat = 0
    
    var body: some View {
        GeometryReader { geometry in
            let amplitudes = trackAudio.track.amplitudes
            let scaleX = geometry.size.width / CGFloat(amplitudes.count * Int(barWidth + barSpacing))
            let scaleY = geometry.size.height / (amplitudes.max() ?? 1)
            
            ZStack {
                WaveformContentView(
                    amplitudes: amplitudes,
                    barWidth: barWidth,
                    barSpacing: barSpacing,
                    scaleX: scaleX,
                    scaleY: scaleY,
                    fillColor: .blue
                )
                
                // Playhead
                let playheadPosition = CGFloat(trackAudio.currentPosition) / trackAudio.track.durationSeconds * geometry.size.width
                Rectangle()
                    .fill(Color.red)
                    .frame(width: 2)
                    .position(x: playheadPosition, y: geometry.size.height / 2)
            }
        }
        .frame(height: 50)
    }
}
