import {Circle, Layout, Rect, Txt, makeScene2D} from '@motion-canvas/2d';
import {all, createRef, easeInOutCubic, waitFor} from '@motion-canvas/core';

export default makeScene2D(function* (view) {
  view.fill('#070a1b');

  const earth = createRef<Circle>();
  const moon = createRef<Circle>();
  const title = createRef<Txt>();

  view.add(
    <Layout width={1080} height={1920}>
      <Txt
        ref={title}
        text={'THE MOON ROTATES'}
        x={0}
        y={-690}
        width={900}
        textAlign={'center'}
        fontFamily={'DejaVu Sans'}
        fontWeight={700}
        fontSize={74}
        fill={'#ffffff'}
        opacity={0}
      />
      <Circle
        ref={earth}
        size={270}
        x={0}
        y={80}
        fill={'#3671ab'}
        stroke={'#add7f6'}
        lineWidth={5}
        scale={0.8}
      />
      <Circle
        ref={moon}
        size={150}
        x={0}
        y={-340}
        fill={'#b8bec7'}
        stroke={'#f5f7fa'}
        lineWidth={4}
      />
      <Rect
        width={650}
        height={92}
        y={650}
        radius={24}
        fill={'#080c17'}
      >
        <Txt
          text={'1 ORBIT  =  1 SPIN'}
          fontFamily={'DejaVu Sans'}
          fontWeight={700}
          fontSize={42}
          fill={'#ffae5b'}
        />
      </Rect>
    </Layout>,
  );

  yield* all(
    title().opacity(1, 0.45),
    earth().scale(1, 0.65, easeInOutCubic),
  );

  // First installed Motion Canvas smoke animation. Astra's JSON director will
  // replace these fixed coordinates with generated scene specs next.
  for (let i = 0; i < 4; i++) {
    yield* moon().position(
      [
        [330, 80],
        [0, 500],
        [-330, 80],
        [0, -340],
      ][i] as [number, number],
      0.75,
      easeInOutCubic,
    );
  }

  yield* waitFor(0.3);
});
