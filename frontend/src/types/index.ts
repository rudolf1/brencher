import type { components } from './api';

export type CommitInfo = components['schemas']['CommitInfo'];
export type BranchCommitPair = [string, string];
export type PipelineStep = components['schemas']['PipelineStep'];
export type EnvironmentDto = components['schemas']['EnvironmentDto'];
export type BranchesData = components['schemas']['BranchesData'];
export type EnvironmentsData = components['schemas']['EnvironmentsData'];
export type WsIncomingMessage = components['schemas']['WsIncomingMessage'];
export type WsUpdatePayload = components['schemas']['WsUpdatePayload'];
export type WsOutgoingMessage = components['schemas']['WsOutgoingMessage'];
