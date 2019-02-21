import requests
import re
import time

class Ticket(object):
	def __init__(self):
		self.url = 'https://kyfw.12306.cn/otn/leftTicket/queryX?'
		self.session = requests.session()
		self.headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36' }

	def GetCityCode(self,citys,code_version):
		print('获取城市代码(版本为:{0})...'.format(code_version))
		url='https://kyfw.12306.cn/otn/resources/js/framework/station_name.js?station_version='+code_version
		result=self.session.get(url=url,headers=self.headers).content.decode('utf-8')
		citys_code={}
		for city in citys:
			codes=re.findall('({0}.*?)\|(.*?)\|'.format(city),result,re.S)
			for item in codes:
				citys_code[item[0]]=item[1]
		print('获取城市代码完成')
		return citys_code

	def GetAllTrain(self,date='2019-03-01',from_s='NCG',to_s='ZZF',t_type='ADULT'):
		para=['leftTicketDTO.train_date=','&leftTicketDTO.from_station=','&leftTicketDTO.to_station=','&purpose_codes=']
		full_url=self.url+para[0]+date+para[1]+from_s+para[2]+to_s+para[3]+t_type;
		response=self.session.get(url=full_url,headers=self.headers).json()
		response=response['data']['result']
		return self.__ParseResponse(response)

	def __ParseResponse(self,response):
		trains=[]
		for item in response:
			tmp=item.split('|')
			trainMsg={
				'name':tmp[3],
				'from':tmp[6],
				'to':tmp[7],
				'time_start':tmp[8],
				'time_end':tmp[9],
				'time_spend':tmp[10]
			}
			trains.append(trainMsg)
		return trains

	def GetCityName(self,city_code,code_version):
		url='https://kyfw.12306.cn/otn/resources/js/framework/station_name.js?station_version='+code_version
		result=self.session.get(url=url,headers=self.headers).content.decode('utf-8')
		p=result.find(city_code)-1
		pm=p
		if p<=0:
			return None
		while True:
			p-=1
			if result[p]=='|':
				break
		return result[p+1:pm]

class GetFastestLine(object):
	def __init__(self,citys,time_area=12,city_code_version="1.9094",date=time.strftime("%Y-%m-%d",time.localtime(time.time()+864000))):
		self.citys=citys.split()
		self.date=date
		self.code_version=city_code_version
		self.time_area=time_area
		self.ticket=Ticket()
		self.citysc=self.ticket.GetCityCode(self.citys,city_code_version)
		self.lines=[]
		self.f_lines=[]

	def Start(self):
		self.__GetLines()
		self.__BuildLine()

	def __GetLines(self):
		print('获取路程信息(按十天后时间:{0})...'.format(self.date))
		for i in range(len(self.citys)-1):
			print('->获取 {0} 到 {1} 的车票信息...'.format(self.citys[i],self.citys[i+1]))
			tmp=self.ticket.GetAllTrain(date=self.date,from_s=self.citysc[self.citys[i]],to_s=self.citysc[self.citys[i+1]])
			self.lines.append(tmp)
		print('获取完成')

	def __BuildLine(self):
		print('计算所有可能的路线...')
		for i in self.lines[0]:
			self.__BuildLine_GetFeasibleLine(0,i,[i])
		print('计算完成')
		print('计算路线耗时...')
		self.__BuildLine_CalcFullTime()
		print('计算完成')
		print('按时间升序排序...')
		self.__BuildLine_SortLines()
		print('完成(共{0}条记录)'.format(len(self.f_lines)))
		input('请按回车键退出')
		
	def __BuildLine_GetFeasibleLine(self,index,train,line):
		if index+1==len(self.lines):
			line[-1]['time_wait']=[0,0]
			self.f_lines.append([item.copy() for item in line])
			return
		for i in self.lines[index+1]:
			time=self.__BuildLine_IsFeasible(train['time_end'],i['time_start'])
			if time != False:
				line[-1]['time_wait']=time
				self.__BuildLine_GetFeasibleLine(index+1,i,line+[i])

	def __BuildLine_IsFeasible(self,pre_train,after_train):
		time=self.__BuildLine_CalcTime(pre_train,after_train)
		if time[0]>self.time_area:
			return False
		elif time[0]==self.time_area and time[1]>0:
			return False
		else:
			return time

	def __BuildLine_CalcTime(self,end,start):
		end=self.__BuildLine_ConvertTime(end)
		start=self.__BuildLine_ConvertTime(start)
		if start[1]<end[1]:
			start[0]-=1
			start[1]+=60
		if start[0]<end[0]:
			start[0]+=24
		return [start[i]-end[i] for i in range(2)]
	
	def __BuildLine_ConvertTime(self,time):
		time=time.split(':')
		return [int(i) for i in time]

	def __BuildLine_CalcFullTime(self):
		for j in self.f_lines:
			time=[0,0]
			for i in j:
				tmp=self.__BuildLine_ConvertTime(i['time_spend'])
				time=[time[k]+tmp[k]+i['time_wait'][k] for k in range(2)]
			j[-1]['time_wait']=[time[0]+int(time[1]/60),time[1]%60]

	def __BuildLine_SortLines(self,page_num=100):
		count=len(self.f_lines)
		for i in range(len(self.f_lines)):
			if i%page_num==0 and i>0:
				print('以上是第{0}到{1}条记录(共{2}条记录)'.format(i-page_num,i,count))
				input('请按回车键输出下一页')
			for j in range(i+1,len(self.f_lines)):
				if self.__BuildLine_IsShorter(self.f_lines[i][-1]['time_wait'],self.f_lines[j][-1]['time_wait']):
					self.f_lines[i],self.f_lines[j]=self.f_lines[j],self.f_lines[i]
			self.__BuildLine_Display(self.f_lines[i])

	def __BuildLine_IsShorter(self,time1,time2):
		if time1[0]<time2[0]:
			return False
		elif time1[0]==time2[0] and time1[1]<=time2[1]:
			return False
		return True

	def __BuildLine_Display(self,line):
		print('┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓')
		print('┃%42s┃'%'全程{0}时{1}分'.format(line[-1]['time_wait'][0],line[-1]['time_wait'][1]))
		print('┃%47s'%'┃')
		for i in range(len(line)):
			print('┃%7s'%line[i]['time_start'],'%18s'%line[i]['time_spend'],'%18s ┃'%line[i]['time_end'])
			from_s=self.__GetCityName(line[i]['from'])
			to_s=self.__GetCityName(line[i]['to'])
			print(self.__BuildLine_DisplayE(0,from_s)+self.__BuildLine_DisplayE(1,line[i]['name'])+self.__BuildLine_DisplayE(2,to_s))
			print('┃%47s'%'┃')
			if i==len(line)-1:
				break
			if i<len(line)-1 and line[i]['to']!=line[i+1]['from']:
				print('┃%14s'%'异站中转,停留{0}时{1}分'.format(line[i]['time_wait'][0],line[i]['time_wait'][1]),'%24s'%'┃')
			else:
				print('┃%11s'%'停留{0}时{1}分'.format(line[i]['time_wait'][0],line[i]['time_wait'][1]),'%31s'%'┃')
			print('┃%47s'%'┃')
		print('┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛')

	def __BuildLine_DisplayE(self,flag,content):
		if flag==0:
			return '┃%{0}s'.format(7-len(content))%content
		elif flag==1:
			return '%19s'%content
		elif flag==2:
			return '%14s'%''+content+' '*(6-2*len(content))+'┃'

	def __GetCityName(self,city_code):
		for i in self.citysc:
			if self.citysc[i]==city_code:
				return i
		tmp=self.ticket.GetCityName(city_code,self.code_version)
		if tmp==None:
			return city_code
		return tmp


if __name__=='__main__':
	getFastestLine=GetFastestLine(input('请依次输入经过的站点(用空格隔开):\n'))
	getFastestLine.Start()
