import SwiftUI
import RealmSwift

struct ScrollableWaveformView: View {
    @ObservedObject var trackAudio: TrackAudio
    @ObservedRealmObject var track: Track
    @GestureState private var dragOffset: CGFloat = 0
    
    let barWidth: CGFloat = 2
    let barSpacing: CGFloat = 2
    let tickHeight: CGFloat = 20
    let labelHeight: CGFloat = 20
    
    var body: some View {
        GeometryReader { geometry in
            let markerHeight = geometry.size.height - tickHeight - labelHeight
            ZStack(alignment: .topLeading) {
                VStack {
                    tickMarksView(geometry: geometry)
                    WaveformContentView(
                        amplitudes: track.amplitudes,
                        barWidth: barWidth,
                        barSpacing: barSpacing,
                        scaleX: 1,
                        scaleY: 1,
                        fillColor: .blue
                    )
                        .frame(height: markerHeight, alignment: .leading)
                        .offset(y: tickHeight + labelHeight)
                }
                .offset(x: calculateOffset(geometry: geometry))
                
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
            }
            .clipped()
        }
        .frame(height: 200)
    }
    
    private func tickMarksView(geometry: GeometryProxy) -> some View {
        let pixelsPerSecond = (barWidth + barSpacing) * CGFloat(Track.AMPLITUDES_PER_SECOND)
        let totalQuarterSeconds = Int(track.durationSeconds * 4) + 1

        return LazyHStack(spacing: 0) {
            ForEach(0..<totalQuarterSeconds, id: \.self) { index in
                VStack(spacing: 0) {
                    Rectangle()
                        .fill(Color.gray)
                        .frame(width: 1, height: index % 4 == 0 ? tickHeight : tickHeight / 2)
                    if index % 4 == 0 {
                        Text(Format.duration(Double(index) / 4.0))
                            .font(.system(size: 8))
                            .frame(width: pixelsPerSecond / 4, alignment: .center)
                    } else {
                        Spacer().frame(height: labelHeight)
                    }
                }
                .frame(width: pixelsPerSecond / 4)
                .offset(x: -pixelsPerSecond / 8) // move frames so center is at x=0
            }
        }.frame(width: geometry.size.width, alignment: .leading)
    }



    private func calculateOffset(geometry: GeometryProxy) -> CGFloat {
        let pixelsPerSecond = (barWidth + barSpacing) * CGFloat(Track.AMPLITUDES_PER_SECOND)
        let currentPositionOffset = CGFloat(trackAudio.currentPosition) * pixelsPerSecond
        let initialOffset = geometry.size.width / 2 // Center the waveform initially
        return initialOffset - currentPositionOffset
    }
}
