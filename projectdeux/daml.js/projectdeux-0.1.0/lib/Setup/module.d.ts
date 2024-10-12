// Generated from Setup.daml
/* eslint-disable @typescript-eslint/camelcase */
/* eslint-disable @typescript-eslint/no-namespace */
/* eslint-disable @typescript-eslint/no-use-before-define */
import * as jtv from '@mojotech/json-type-validation';
import * as damlTypes from '@daml/types';
/* eslint-disable-next-line @typescript-eslint/no-unused-vars */
import * as damlLedger from '@daml/ledger';

import * as pkg65b964c560e408a64f1427e9d6a287d9ae3788b1525f10e331097a63fb2682de from '@daml.js/daml-script-2.9.4';

export declare type TestUser = {
  alias: string;
  public: damlTypes.Party;
  participantName: damlTypes.Optional<pkg65b964c560e408a64f1427e9d6a287d9ae3788b1525f10e331097a63fb2682de.Daml.Script.ParticipantName>;
};

export declare const TestUser:
  damlTypes.Serializable<TestUser> & {
  }
;


export declare type Parties = {
  alice: damlTypes.Party;
  bob: damlTypes.Party;
  charlie: damlTypes.Party;
  public: damlTypes.Party;
};

export declare const Parties:
  damlTypes.Serializable<Parties> & {
  }
;

