# certs/

Public certificates only. **Never commit a `.pfx`, `.p12` or `.key` file.** `.gitignore` blocks them.

## devteam-codesign.cer: Windows code signing

| | |
|---|---|
| Subject / Issuer | `CN=ScienceSoft AI DevTeam` (self-signed) |
| Usage | Digital Signature, Code Signing |
| Valid | 2026-11-15 to **2027-11-15** |
| SHA-1 thumbprint | `3B5ABCA3ACCC30D951E31322D070A4FF3690F198` |

`build-windows.yml` checks that the installer's signer has this thumbprint.
`WIN_PUBLISHER_NAME` in `devteam.conf` must equal the CN.

### Where the private key lives

- **CI:** GitHub Actions secrets on this repo. electron-builder reads them directly.
  - `WIN_CSC_LINK` holds the base64 of the `.pfx`.
  - `WIN_CSC_KEY_PASSWORD` holds its password.

  ```powershell
  [Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\path\devteam-codesign.pfx")) | Set-Content pfx.b64
  gh secret set WIN_CSC_LINK --repo sciencesoft-ai/devteam < pfx.b64
  gh secret set WIN_CSC_KEY_PASSWORD --repo sciencesoft-ai/devteam
  Remove-Item pfx.b64
  ```

- **Local builds:** keep the `.pfx` outside the repo and set
  `WIN_CSC_LINK=C:\path\devteam-codesign.pfx` and `WIN_CSC_KEY_PASSWORD=...` before running the build.

### Trusting the certificate on user machines

Windows doesn't trust a self-signed certificate by default. Until it's trusted, users see
"Unknown publisher" and SmartScreen warnings. Import the certificate into **both** stores.

Per machine, as admin:

```powershell
Import-Certificate -FilePath devteam-codesign.cer -CertStoreLocation Cert:\LocalMachine\Root
Import-Certificate -FilePath devteam-codesign.cer -CertStoreLocation Cert:\LocalMachine\TrustedPublisher
```

At scale, deploy it with Group Policy or Intune:

- GPO: Computer Configuration → Policies → Windows Settings → Security Settings → Public Key Policies. Add it under both *Trusted Root Certification Authorities* and *Trusted Publishers*.
- Intune: use a *Trusted certificate* profile.

A self-signed certificate works for internal rollout only. A public release needs a certificate from a commercial CA, OV or EV. SmartScreen reputation also builds per certificate.

### Renewal (before 2027-11-15)

Installed apps check that each update is signed by `WIN_PUBLISHER_NAME`. When you renew:

1. Keep the **same CN**.
2. Replace `devteam-codesign.cer` here and the two secrets.
3. Push the new `.cer` to user machines **before** shipping the first build signed with it.
