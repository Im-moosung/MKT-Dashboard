export function vegaField(field: string | undefined): string | undefined {
  if (field === undefined) return undefined;
  return field.replace(/\\/g, '\\\\').replace(/\./g, '\\.');
}
