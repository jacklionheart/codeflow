import SwiftUI

struct RecorderView: View {
    @ObservedObject var recorder: Recorder

    var parent: Track?
    var body: some View {
        VStack {
            Spacer()
           // WaveformView(waveform: recorder.waveform)
            if (recorder.active) {
                Text(recorder.name).bold()
                Text(Format.duration(recorder.elapsedTime)).font(.headline)
            }
            Spacer()
            RecorderButton(recorder: recorder, start: {
                AppLogger.ui.debug("RecorderView start")
                recorder.start()
            }, stop: {
                AppLogger.ui.debug("RecorderView stop")
                recorder.stop(to: parent)
            })
        }
        .frame(maxWidth: .infinity, maxHeight: recorder.active ? 200 : 100)
        .background {
            Color.gray.opacity(0.1).ignoresSafeArea(.all)
        }
        .onAppear {
            AppLogger.ui.debug("RecorderView.onAppear active:\(recorder.active)")
        }
        .onDisappear {
            AppLogger.ui.debug("RecorderView.onDisappear active:\(recorder.active)")
        }
    }
    
}

struct RecorderButton: View {
    @ObservedObject var recorder: Recorder
    var start: (() -> Void)
    var stop: (() -> Void)
    
    var body: some View {
        Button(action: {
            withAnimation(.easeInOut) {
                AppLogger.ui.debug("RecorderView.RecorderButton.action active:\(recorder.active)")
                if recorder.active {
                    stop()
                } else {
                    start()
                }
            }
        }) {
            ZStack {
                Circle()
                    .stroke(lineWidth: 3)
                    .foregroundColor(.gray)
                    .frame(width: 60, height: 60)
                if !recorder.active {
                    Circle()
                        .foregroundColor(.red)
                        .frame(width: 50, height: 50)
                } else {
                    RoundedRectangle(cornerRadius: 5)
                        .foregroundColor(.red)
                        .frame(width: 30, height: 30)
                }
            }
        }
    }
}
