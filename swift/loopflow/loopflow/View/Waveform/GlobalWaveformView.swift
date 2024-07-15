import SwiftUI
import RealmSwift

struct GlobalWaveformView: View {
    @ObservedObject var trackAudio: TrackAudio
    @ObservedRealmObject var track: Track
    @State private var draggedMarker: MarkerType?
    @State private var pendingChange: (MarkerType, Double)?
    @State private var debounceTimer: Timer?

    let barWidth: CGFloat = 1
    let barSpacing: CGFloat = 1
    
    enum MarkerType {
        case start, stop
    }
    
    
    var body: some View {
        GeometryReader { geometry in
            let amplitudes = track.sourceAmplitudes
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
                    .position(x: (CGFloat(track.startSeconds) + CGFloat(track.durationSeconds) / 2) / CGFloat(track.sourceDurationSeconds) * geometry.size.width,
                              y: geometry.size.height / 2)


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
                    position: CGFloat(trackAudio.currentPosition + track.startSeconds) / track.sourceDurationSeconds * geometry.size.width,
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

                // Update the pending change
                pendingChange = (markerType, newTime)

                // Invalidate existing timer and start a new one
                debounceTimer?.invalidate()
                debounceTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: false) { _ in
                    self.applyPendingChange()
                }
            }
            .onEnded { _ in
                // Apply any pending change immediately when the gesture ends
                debounceTimer?.invalidate()
                applyPendingChange()
            }
    }

    private func applyPendingChange() {
        guard let (markerType, newTime) = pendingChange else { return }

        writeToRealm {
            let thawedTrack = track.thaw()!
            switch markerType {
            case .start:
                if newTime < thawedTrack.stopSeconds {
                    thawedTrack.startSeconds = newTime
                    print("Updated start time: \(thawedTrack.startSeconds)")
                }
            case .stop:
                if newTime > thawedTrack.startSeconds {
                    thawedTrack.stopSeconds = newTime
                    print("Updated stop time: \(thawedTrack.stopSeconds)")
                }
            }
        }

        // Clear the pending change
        pendingChange = nil
    }

}
