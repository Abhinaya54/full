# Vercel Deployment & Git Setup TODO

## Plan Steps
1. [ ] Update Git remote to https://github.com/Abhinaya54/full.git (`git remote set-url origin https://github.com/Abhinaya54/full.git`)
2. [ ] Create .gitignore (venv/, __pycache__/)
3. [ ] `git add app.py requirements.txt vercel.json TODO.md .gitignore`
4. [ ] `git commit -m "Prepare for Vercel deployment: add requirements.txt, vercel.json, TODO.md, .gitignore; update app.py"`
5. [ ] `git push origin main`
6. [x] Create requirements.txt ✅
7. [x] Create vercel.json ✅
8. [x] Update app.py for MONGO_URI ✅ (already uses env var)
9. [ ] Vercel CLI setup & deploy (`npm i -g vercel`, `vercel login`, `vercel`)
10. [ ] Set MONGO_URI in Vercel dashboard
11. [ ] Test live site

## Progress
Git remote & commit pending. Deploy after push.
