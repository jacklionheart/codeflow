import SwiftUI

struct ScrollingWaveformView: View {
    @ObservedObject var trackAudio: TrackAudio
    
    let barWidth: CGFloat = 2
    let barSpacing: CGFloat = 1
    let tickHeight: CGFloat = 20
    let labelHeight: CGFloat = 20
    
    var body: some View {
        GeometryReader { geometry in
            let offset = calculateOffset(geometry: geometry)
            ZStack(alignment: .topLeading) {
                VStack {
                    tickMarksView(geometry: geometry)
                        .offset(x: offset)
                    WaveformContentView(
                        amplitudes: trackAudio.track.amplitudes,
                        barWidth: barWidth,
                        barSpacing: barSpacing,
                        scaleX: 1,
                        scaleY: 1,
                        fillColor: .blue
                    )
                    .frame(height: geometry.size.height - tickHeight - labelHeight)
                    .offset(x: offset, y: tickHeight + labelHeight)
                }
                
                // Playhead
                TimelineMarkerView(
                    position: geometry.size.width / 2,
                    height: markerHeight,
                    color: .red,
                    width: 2,
                    showTopIndicator: true,
                    showBottomIndicator: true
                )
                .offset(y: tickHeight + labelHeight)
                
                // Start marker
                TimelineMarkerView(
                    position: CGFloat(trackAudio.track.startTimeSeconds) / trackAudio.track.playbackDurationSeconds * geometry.size.width,
                    height: markerHeight,
                    color: .green,
                    width: 3,
                    showTopIndicator: true,
                    showBottomIndicator: false
                )
                .offset(y: tickHeight + labelHeight)
                
                // Stop marker
                TimelineMarkerView(
                    position: CGFloat(trackAudio.track.stopTimeSeconds) / trackAudio.track.playbackDurationSeconds * geometry.size.width,
                    height: markerHeight,
                    color: .blue,
                    width: 3,
                    showTopIndicator: true,
                    showBottomIndicator: false
                )
                .offset(y: tickHeight + labelHeight)            }
            .clipped()
        }
        .frame(height: 240)
    }
    private func tickMarksView(geometry: GeometryProxy) -> some View {
        let pixelsPerSecond = (barWidth + barSpacing) * CGFloat(Track.AMPLITUDES_PER_SECOND)
        let totalQuarterSeconds = Int(trackAudio.track.durationSeconds * 4) + 1
        
        return LazyHStack(spacing: 0) {
            ForEach(0..<totalQuarterSeconds, id: \.self) { index in
                VStack(spacing: 0) {
                    Rectangle()
                        .fill(Color.gray)
                        .frame(width: 1, height: index % 4 == 0 ? tickHeight : tickHeight / 2)
                    if index % 4 == 0 {
                        Text(Format.duration(Double(index) / 4.0))
                            .font(.system(size: 8))
                    //        .frame(width: pixelsPerSecond, alignment: .leading)
                    //         .offset(x: 2) // Slight offset to prevent overlap with tick mark
                    } else {
                        Spacer().frame(height: labelHeight)
                    }
                }
                .frame(width: pixelsPerSecond / 4) // alignment: .leading)
            }
        }
    }
    
    private func calculateOffset(geometry: GeometryProxy) -> CGFloat {
        let pixelsPerSecond = (barWidth + barSpacing) * CGFloat(Track.AMPLITUDES_PER_SECOND)
        let currentPositionOffset = CGFloat(trackAudio.currentPosition) * pixelsPerSecond
        let initialOffset = geometry.size.width / 2 // Center the waveform initially
        return initialOffset - currentPositionOffset
    }
}
