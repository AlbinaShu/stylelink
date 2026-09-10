export function maskEmail(email: string) {
    const [local, domain] = email.split('@');

    if (!local || !domain) { return email; }

    return `${local.slice(0, 2)}***@${domain}`;
}
