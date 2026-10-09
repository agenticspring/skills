# Powerstone + Library (Bookmark) — proven PCM endpoints

Tested 2026-07-20 against:
- bookId `36184308800959105`
- URL `https://m.webnovel.com/book/naruto-i-slapped-the-white-fang-on-day-one_36184308800959105`
- Fresh authed mobile session (`login/login` + csrf)

Auth gate is the same as avatar: `GET /go/pcm/login/login?_csrfToken=&ticket=&guid=` must return `code=0` first.

## Powerstone

### Balance / rank on a book
```
GET /go/pcm/book/getRewardVotingPopup?bookId={id}&bookType=0&_csrfToken=
```
- Use **bookType=0** even if `getBookDetail.bookInfo.bookType` is 2 (other values → `1001 parameters error`).
- Response: `data.power.balance`, `nums`, `rank`.

### User power inventory
```
GET /go/pcm/user/userInfoAjax?_csrfToken=
```
- `profile.availablePower`, `profile.totalPower`
- New accounts often start with `availablePower: 1`.

### Vote / spend powerstone
```
POST /go/pcm/powerStone/vote
Content-Type: application/x-www-form-urlencoded
Origin: https://m.webnovel.com
Referer: https://m.webnovel.com/book/...

bookId={id}
amount={n}          # <= availablePower
novelType=0
_csrfToken={csrf}
```
Success sample:
```json
{"code":0,"data":{"rewardSS":5,"rewardMessage":"1powerstone was successfully used."},"msg":"Success"}
```
After spend: balance drops; book `nums` increments.

Related (not fully exercised this session):
- `GET /go/pcm/goldenTicket/vote?bookId=&amount=&novelType=`
- `create /go/pcm/spiritStone/checkIn` (daily check-in, not powerstone vote)

## Bookmark = Library add

Mobile "bookmark" is **Add to Library**.

### Add
```
POST /go/pcm/library/addLibraryItemsAjax
Content-Type: application/x-www-form-urlencoded

bookIds={id}        # note plural bookIds
novelType=0
_csrfToken={csrf}
```
Success: `{"code":0,"data":null,"msg":"Success"}`

### List / remove
```
GET  /go/pcm/library/library?_csrfToken=&orderBy=1&pageIndex=1&pageSize=20&encryptType=1
POST /go/pcm/library/deleteLibraryItemsAjax
```
- List with `encryptType=1` returns encrypted `data.content` blob.
- Frontend also uses `setReadingProgressAjax` while reading.

## JS reverse sources
- `_app-*.js`: path defs for `powerStone/vote`, goldenTicket
- `583-*.js`: `addLibrary({bookIds, novelType})`
- Book page chunk: PowerStone UI enum `Gift=1, GoldenTicket=2, PowerStone=3`

## Live proof log
Account userid `4507220385`:
1. reward popup balance=1
2. vote amount=1 → Success + rewardSS 5
3. addLibraryItemsAjax → Success
4. recheck availablePower=0, book nums 24→25
