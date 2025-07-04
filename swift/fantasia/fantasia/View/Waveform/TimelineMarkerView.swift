//
//  TimelineMarkerVIew.swift
//  fantasia
//
//  Created by Jack Heart on 7/2/24.
//

import SwiftUI

struct TimelineMarkerView: View {
    let position: CGFloat
    let height: CGFloat
    let color: Color
    let width: CGFloat
    let showTopIndicator: Bool
    let showBottomIndicator: Bool
    
    var body: some View {
        ZStack(alignment: .top) {
            Rectangle()
                .fill(color)
                .frame(width: width, height: height)
            
            if showTopIndicator {
                Circle()
                    .fill(color)
                    .frame(width: 10, height: 10)
                    .offset(y: -5)
            }
            
            if showBottomIndicator {
                Circle()
                    .fill(color)
                    .frame(width: 10, height: 10)
                    .offset(y: height - 10)
            }
        }
        .position(x: position, y: height / 2)
    }
}
