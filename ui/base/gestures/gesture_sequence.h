// Copyright (c) 2012 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef UI_BASE_GESTURES_GESTURE_SEQUENCE_H_
#define UI_BASE_GESTURES_GESTURE_SEQUENCE_H_
#pragma once

#include "base/timer.h"
#include "ui/base/events.h"
#include "ui/base/gestures/gesture_point.h"
#include "ui/base/gestures/gesture_recognizer.h"

namespace ui {
class TouchEvent;
class GestureEvent;

// Gesture state.
enum GestureState {
  GS_NO_GESTURE,
  GS_PENDING_SYNTHETIC_CLICK,
  GS_SCROLL,
  GS_PINCH,
  GS_THREE_FINGER_SWIPE
};

enum ScrollType {
  ST_FREE,
  ST_HORIZONTAL,
  ST_VERTICAL,
};

// A GestureSequence recognizes gestures from touch sequences.
class UI_EXPORT GestureSequence {
 public:
  explicit GestureSequence(GestureEventHelper* consumer);
  virtual ~GestureSequence();

  typedef GestureRecognizer::Gestures Gestures;

  // Invoked for each touch event that could contribute to the current gesture.
  // Returns list of  zero or more GestureEvents identified after processing
  // TouchEvent.
  // Caller would be responsible for freeing up Gestures.
  virtual Gestures* ProcessTouchEventForGesture(const TouchEvent& event,
                                                ui::TouchStatus status);
  const GesturePoint* points() const { return points_; }
  int point_count() const { return point_count_; }

  // Maximum number of points in a single gesture.
  static const int kMaxGesturePoints = 12;

 protected:
  virtual base::OneShotTimer<GestureSequence>* CreateTimer();
  base::OneShotTimer<GestureSequence>* long_press_timer() {
    return long_press_timer_.get();
  }

 private:
  void Reset();

  GesturePoint& GesturePointForEvent(const TouchEvent& event);

  // Do a linear scan through points_ to find the GesturePoint
  // with id |point_id|.
  GesturePoint* GetPointByPointId(int point_id);

  // Functions to be called to add GestureEvents, after successful recognition.

  // Tap gestures.
  void AppendTapDownGestureEvent(const GesturePoint& point, Gestures* gestures);
  void AppendClickGestureEvent(const GesturePoint& point, Gestures* gestures);
  void AppendDoubleClickGestureEvent(const GesturePoint& point,
                                     Gestures* gestures);
  void AppendLongPressGestureEvent();

  // Scroll gestures.
  void AppendScrollGestureBegin(const GesturePoint& point,
                                const gfx::Point& location,
                                Gestures* gestures);
  void AppendScrollGestureEnd(const GesturePoint& point,
                              const gfx::Point& location,
                              Gestures* gestures,
                              float x_velocity,
                              float y_velocity);
  void AppendScrollGestureUpdate(const GesturePoint& point,
                                 const gfx::Point& location,
                                 Gestures* gestures);

  // Pinch gestures.
  void AppendPinchGestureBegin(const GesturePoint& p1,
                               const GesturePoint& p2,
                               Gestures* gestures);
  void AppendPinchGestureEnd(const GesturePoint& p1,
                             const GesturePoint& p2,
                             float scale,
                             Gestures* gestures);
  void AppendPinchGestureUpdate(const GesturePoint& p1,
                                const GesturePoint& p2,
                                float scale,
                                Gestures* gestures);

  void AppendThreeFingerSwipeGestureEvent(const GesturePoint& p1,
                                          const GesturePoint& p2,
                                          const GesturePoint& p3,
                                          float x_velocity,
                                          float y_velocity,
                                          Gestures* gestures);

  void set_state(const GestureState state ) { state_ = state; }

  // Various GestureTransitionFunctions for a signature.
  // There is, 1:many mapping from GestureTransitionFunction to Signature
  // But a Signature have only one GestureTransitionFunction.
  bool Click(const TouchEvent& event,
             const GesturePoint& point,
             Gestures* gestures);
  bool ScrollStart(const TouchEvent& event,
                             GesturePoint& point,
                             Gestures* gestures);
  void BreakRailScroll(const TouchEvent& event,
                               GesturePoint& point,
                               Gestures* gestures);
  bool ScrollUpdate(const TouchEvent& event,
                    const GesturePoint& point,
                    Gestures* gestures);
  bool NoGesture(const TouchEvent& event,
                 const GesturePoint& point,
                 Gestures* gestures);
  bool TouchDown(const TouchEvent& event,
                 const GesturePoint& point,
                 Gestures* gestures);
  bool ScrollEnd(const TouchEvent& event,
                 GesturePoint& point,
                 Gestures* gestures);
  bool PinchStart(const TouchEvent& event,
                  const GesturePoint& point,
                  Gestures* gestures);
  bool PinchUpdate(const TouchEvent& event,
                   const GesturePoint& point,
                   Gestures* gestures);
  bool PinchEnd(const TouchEvent& event,
                const GesturePoint& point,
                Gestures* gestures);
  bool ThreeFingerSwipeUpdate(const TouchEvent& event,
                              const GesturePoint& point,
                              Gestures* gestures);

  // Current state of gesture recognizer.
  GestureState state_;

  // ui::EventFlags.
  int flags_;

  // The distance between the two points at PINCH_START.
  float pinch_distance_start_;

  // This distance is updated after each PINCH_UPDATE.
  float pinch_distance_current_;

  ScrollType scroll_type_;
  bool three_finger_swipe_has_fired_;
  scoped_ptr<base::OneShotTimer<GestureSequence> > long_press_timer_;

  GesturePoint points_[kMaxGesturePoints];
  int point_count_;

  GestureEventHelper* helper_;

  DISALLOW_COPY_AND_ASSIGN(GestureSequence);
};

}  // namespace ui

#endif  // UI_BASE_GESTURES_GESTURE_SEQUENCE_H_
