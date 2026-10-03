import React from 'react';
import {Composition} from 'remotion';
import {Reel} from './Reel';
import {FrReel, FR_DURATION} from './FrReel';
export const Root: React.FC = () => (
  <>
    <Composition id="TableReel" component={Reel} durationInFrames={450} fps={30} width={1080} height={1920} />
    <Composition id="FrReel" component={FrReel} durationInFrames={FR_DURATION} fps={30} width={1080} height={1920} />
  </>
);
