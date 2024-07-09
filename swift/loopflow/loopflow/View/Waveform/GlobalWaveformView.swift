import SwiftUI
import RealmSwift

struct GlobalWaveformView: View {
    @ObservedObject var trackAudio: TrackAudio
    @ObservedRealmObject var track: Track
    @State private var draggedMarker: MarkerType?
    
    let barWidth: CGFloat = 1
    let barSpacing: CGFloat = 0
    
    enum MarkerType {
        case start, stop
    }
    
    
    var body: some View {
        GeometryReader { geometry in
            let amplitudes = track.amplitudes
            let scaleX = geometry.size.width / CGFloat(amplitudes.count * Int(barWidth + barSpacing))
            let scaleY = geometry.size.height / (amplitudes.max() ?? 1)
            
            ZStack {
                // Waveform
                WaveformContentView(
                    amplitudes: amplitudes,
                    barWidth: barWidth,
                    barSpacing: barSpacing,
                    scaleX: scaleX,
                    scaleY: scaleY,
                    fillColor: .blue
                )
                
                // Highlighted area
                Rectangle()
                    .fill(Color.blue.opacity(0.2))
                    .frame(width: CGFloat(track.durationSeconds) / track.sourceDurationSeconds * geometry.size.width)
                    .offset(x: CGFloat(track.startSeconds) / track.sourceDurationSeconds * geometry.size.width)
                
                // Start marker
                TimelineMarkerView(
                    position: CGFloat(track.startSeconds) / track.sourceDurationSeconds * geometry.size.width,
                    height: geometry.size.height,
                    color: .blue,
                    width: 2,
                    showTopIndicator: true,
                    showBottomIndicator: true
                )
                .gesture(dragGesture(for: .start, geometry: geometry))
                
                // Stop marker
                TimelineMarkerView(
                    position: CGFloat(track.stopSeconds) / track.sourceDurationSeconds * geometry.size.width,
                    height: geometry.size.height,
                    color: .blue,
                    width: 2,
                    showTopIndicator: true,
                    showBottomIndicator: true
                )
                .gesture(dragGesture(for: .stop, geometry: geometry))
                
                // Playhead
                TimelineMarkerView(
                    position: CGFloat(trackAudio.currentPosition) / track.sourceDurationSeconds * geometry.size.width,
                    height: geometry.size.height,
                    color: .red,
                    width: 2,
                    showTopIndicator: false,
                    showBottomIndicator: false
                )
            }
        }
        .frame(height: 50)
    }
    
    private func dragGesture(for markerType: MarkerType, geometry: GeometryProxy) -> some Gesture {
            DragGesture(minimumDistance: 2)
                .onChanged { value in
                    let startX = value.startLocation.x
                    let currentX = value.location.x
                    let totalWidth = geometry.size.width

                    print("""
                        ON CHANGED:
                        Start X: \(startX)
                        Current X: \(currentX)
                        Total Width: \(totalWidth)
                        """)

                    let percentage = max(0, min(1, currentX / totalWidth))
                    let newTime = track.sourceDurationSeconds * Double(percentage)

                    print("Calculated new time: \(newTime)")

                    switch markerType {
                    case .start:
                        if newTime < track.stopSeconds {
                            writeToRealm {
                                let thawedTrack = track.thaw()!
                                thawedTrack.startSeconds = newTime
                                print("Updated start time: \(thawedTrack.startSeconds)")
                            }
                        }
                    case .stop:
                        if newTime > track.startSeconds {
                            writeToRealm {
                                let thawedTrack = track.thaw()!
                                thawedTrack.stopSeconds = newTime
                                print("Updated stop time: \(thawedTrack.stopSeconds)")
                            }
                        }
                    }
                }
        }
}
