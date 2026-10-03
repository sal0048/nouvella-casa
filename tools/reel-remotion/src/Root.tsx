import React from 'react';
import {Composition} from 'remotion';
import {Reel} from './Reel';
import {FrReel, FR_DURATION} from './FrReel';
import {NoyaSlide} from './NoyaSlide';
import {NoyaReach} from './NoyaReach';
export const Root: React.FC = () => (
  <>
    <Composition id="TableReel" component={Reel} durationInFrames={450} fps={30} width={1080} height={1920} />
    <Composition id="FrReel" component={FrReel} durationInFrames={FR_DURATION} fps={30} width={1080} height={1920} />
    <Composition id="NoyaSlide" component={NoyaSlide} durationInFrames={1} fps={30} width={1080} height={1350} defaultProps={{model: 'ORION', idx: 0}} />
    <Composition id="NoyaReach" component={NoyaReach} durationInFrames={1} fps={30} width={1080} height={1350} defaultProps={{model: 'HANA', idx: 0}} />
  </>
);
