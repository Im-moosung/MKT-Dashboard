const DATA_SOURCE_LABELS: Record<string, string> = {
  AdsCampaign: '부분 실데이터',
  Orders: '데모',
  Surveys: '데모',
};

export function dataSourceLabelForMember(memberName: string): string | null {
  const cubeName = memberName.split('.')[0];
  return DATA_SOURCE_LABELS[cubeName] ?? null;
}

export function sourceAwareTitle(member: { name: string; title?: string }): string {
  const title = member.title || member.name;
  const sourceLabel = dataSourceLabelForMember(member.name);
  return sourceLabel ? `${title} · ${sourceLabel}` : title;
}
