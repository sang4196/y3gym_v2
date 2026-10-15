import { pathToFileURL, fileURLToPath } from 'node:url';
import path from 'node:path';
export async function resolve(specifier,context,nextResolve) {
 const run=process.env.Y3GYM_QA_RUN_DIR,project=process.env.Y3GYM_QA_PROJECT_ROOT;
 if(run&&project&&context.parentURL?.startsWith(pathToFileURL(run+'/source/').href)&&specifier.endsWith('prototype/node_modules/@playwright/test/index.mjs')) {
  return {url:pathToFileURL(path.join(project,'backend/scripts/qa_browser_guard.mjs')).href,shortCircuit:true};
 }
 return nextResolve(specifier,context);
}
