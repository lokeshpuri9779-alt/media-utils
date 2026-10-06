import {Circle, Rect, Txt, makeScene2D} from '@motion-canvas/2d';
import {all, createRef, easeInOutCubic, waitFor} from '@motion-canvas/core';

export default makeScene2D(function* (view) {
  view.fill('#080c17');

  const moon = createRef<Circle>();
  const title = createRef<Txt>();
  const label = createRef<Txt>();

  view.add(
    <>
      <Txt
        ref={title}
        text={'1 ORBIT = 1 SPIN'}
        y={-720}
        fontFamily={'Arial'}
        fontWeight={800}
        fontSize={76}
        fill={'#ffffff'}
        opacity={0}
      />
      <Circle
        width={720}
        height={520}
        stroke={'#465270'}
        lineWidth={6}
      />
      <Circle
        size={190}
        fill={'#3671ab'}
        stroke={'#add7f6'}
        lineWidth={6}
      >
        <Txt
          text={'EARTH'}
          fontFamily={'Arial'}
          fontWeight={700}
          fontSize={36}
          fill={'#ffffff'}
        />
      </Circle>
      <Rect
        width={700}
        height={120}
        y={620}
        radius={30}
        fill={'#080c17'}
        stroke={'#1f2c45'}
        lineWidth={3}
      >
        <Txt
          ref={label}
          text={'THE SAME FACE STAYS TOWARD EARTH'}
          fontFamily={'Arial'}
          fontWeight={700}
          fontSize={38}
          fill={'#ffffff'}
          opacity={0}
        />
      </Rect>
      <Circle
        ref={moon}
        size={145}
        x={0}
        y={-260}
        fill={'#c4c8cf'}
        stroke={'#f6f7fa'}
        lineWidth={5}
      >
        <Circle
          size={28}
          x={0}
          y={58}
          fill={'#ffae5b'}
          stroke={'#ffffff'}
          lineWidth={4}
        />
      </Circle>
    </>,
  );

  yield* all(title().opacity(1, 0.45), label().opacity(1, 0.45));
  yield* all(
    moon().position.x(340, 1.25, easeInOutCubic),
    moon().position.y(0, 1.25, easeInOutCubic),
    moon().rotation(90, 1.25, easeInOutCubic),
  );
  yield* all(
    moon().position.x(0, 1.25, easeInOutCubic),
    moon().position.y(260, 1.25, easeInOutCubic),
    moon().rotation(180, 1.25, easeInOutCubic),
  );
  yield* all(
    moon().position.x(-340, 1.25, easeInOutCubic),
    moon().position.y(0, 1.25, easeInOutCubic),
    moon().rotation(270, 1.25, easeInOutCubic),
  );
  yield* all(
    moon().position.x(0, 1.25, easeInOutCubic),
    moon().position.y(-260, 1.25, easeInOutCubic),
    moon().rotation(360, 1.25, easeInOutCubic),
  );
  yield* waitFor(0.5);
});
