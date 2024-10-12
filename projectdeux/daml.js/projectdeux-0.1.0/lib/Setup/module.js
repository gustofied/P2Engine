"use strict";
/* eslint-disable-next-line no-unused-vars */
function __export(m) {
/* eslint-disable-next-line no-prototype-builtins */
    for (var p in m) if (!exports.hasOwnProperty(p)) exports[p] = m[p];
}
Object.defineProperty(exports, "__esModule", { value: true });
/* eslint-disable-next-line no-unused-vars */
var jtv = require('@mojotech/json-type-validation');
/* eslint-disable-next-line no-unused-vars */
var damlTypes = require('@daml/types');
/* eslint-disable-next-line no-unused-vars */
var damlLedger = require('@daml/ledger');

var pkg65b964c560e408a64f1427e9d6a287d9ae3788b1525f10e331097a63fb2682de = require('@daml.js/daml-script-2.9.4');


exports.TestUser = {
  decoder: damlTypes.lazyMemo(function () { return jtv.object({alias: damlTypes.Text.decoder, public: damlTypes.Party.decoder, participantName: damlTypes.Optional(pkg65b964c560e408a64f1427e9d6a287d9ae3788b1525f10e331097a63fb2682de.Daml.Script.ParticipantName).decoder, }); }),
  encode: function (__typed__) {
  return {
    alias: damlTypes.Text.encode(__typed__.alias),
    public: damlTypes.Party.encode(__typed__.public),
    participantName: damlTypes.Optional(pkg65b964c560e408a64f1427e9d6a287d9ae3788b1525f10e331097a63fb2682de.Daml.Script.ParticipantName).encode(__typed__.participantName),
  };
}
,
};



exports.Parties = {
  decoder: damlTypes.lazyMemo(function () { return jtv.object({alice: damlTypes.Party.decoder, bob: damlTypes.Party.decoder, charlie: damlTypes.Party.decoder, public: damlTypes.Party.decoder, }); }),
  encode: function (__typed__) {
  return {
    alice: damlTypes.Party.encode(__typed__.alice),
    bob: damlTypes.Party.encode(__typed__.bob),
    charlie: damlTypes.Party.encode(__typed__.charlie),
    public: damlTypes.Party.encode(__typed__.public),
  };
}
,
};

