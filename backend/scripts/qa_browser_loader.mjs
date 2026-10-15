// Managed copied QA imports use existing read-only dependency binaries.
import { register } from 'node:module';
register('./qa_browser_resolver.mjs', import.meta.url);
